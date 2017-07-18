import json
import datetime
import time
import os
import dateutil.parser
import logging

from dataquery import DataQuery
from dataquery import DataMetric
from databot_session import DataBot_Session
from humanreadable import HumanReadable

import boto3

logger = logging.getLogger()
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)
#logger.setLevel(logging.WARN)

def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def confirm_intent(session_attributes, intent_name, slots, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message, card):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message,
        }
    }

    if len(card) > 0:
        response['dialogAction']['responseCard'] = card

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

def request_is_invalid(query, metric, intent_request):
    invalid_query  = query.validate()
    invalid_metric = metric.validate()

    if len(invalid_query) > 0 or len(invalid_metric) > 0:
        logger.info("validate query/metric:{}/{}".format(json.dumps(invalid_query), json.dumps(invalid_metric)))

        slots = intent_request['currentIntent']['slots']

        first_invalid_slot = False
        for invalid_slot in invalid_query:
            if first_invalid_slot == False:
                first_invalid_slot = invalid_slot['parameter']
            slots[invalid_slot['parameter']] = None

        for invalid_slot in invalid_metric:
            if first_invalid_slot == False:
                first_invalid_slot = invalid_slot['parameter']
            slots[invalid_slot['parameter']] = None

        message = HumanReadable.DataQuery_validate(invalid_query, invalid_metric)

        ## DEBUG!
        message += " - "+query.toJson()+"|"+metric.toJson()

        return elicit_slot(
            intent_request['sessionAttributes'],
            intent_request['currentIntent']['name'],
            slots,
            first_invalid_slot,
            {
                'contentType': 'PlainText',
                'content': message
            })
    return False

def get_session(session):
    if not 'session_id' in session or session['session_id'] is None:
        logger.info("Session id not set, crating new.")
        session = DataBot_Session.create()
    else:
        logger.info("Session id set, using {}".format(session['session_id']))
        session = DataBot_Session(session['session_id'])

    return session

def publish_query(session_id, results):
    lambda_client = boto3.client('lambda')
    lambda_client.invoke(
        FunctionName="databot_session_publish",
        InvocationType='Event',
        Payload=json.dumps({'session_id':session_id, 'results': results})
    )

def notify_publish(session_id):
    lambda_client = boto3.client('lambda')
    lambda_client.invoke(
        FunctionName="databot_session_publish",
        InvocationType='Event',
        Payload=json.dumps({'session_id':session_id})
    )


def process_query(intent_request, query, metric):
    session = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    data_session = get_session(session)
    if data_session is None:
        logger.warn("Failed to create Session. Proceeding anyway...")
    else:
        session['session_id'] = data_session.session_id

    session['current_query'] = query.toJson()
    session['current_metric'] = metric.toJson()

    logger.info('query/metric={}/{}'.format(query.toJson(), metric.toJson()))

    invalid = request_is_invalid(query, metric, intent_request)
    if invalid != False:
        return invalid

    if intent_request['invocationSource'] == 'DialogCodeHook':
        return delegate(session, intent_request['currentIntent']['slots'])

    if not data_session is None:
        notify_publish(data_session.session_id)

    result = metric.calc_on_query(query)

    if not data_session is None:
        res = result.results
        data_session.update(query, metric, result)
        publish_query(data_session.session_id, res)

    session['current_result'] = result.toJson()

    return close(
        session,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': '{} '.format(HumanReadable.dataMetricResult(result, query, data_session.session_id, True))
        },
        {}
    )

# filter, metric, from, period
def selectMetricFromPeriod(intent_request):
    query  = DataQuery(intent_request['currentIntent']['slots'])
    metric = DataMetric(intent_request['currentIntent']['slots'], query.query_from)

    logger.warn(query.toJson())

    return process_query(intent_request, query, metric)


def SelectBooleanFromPeriod(intent_request):
    query  = DataQuery(intent_request['currentIntent']['slots'])
    metric = DataMetric({
        'metric': 'exists'
    }, query.query_from)

    return process_query(intent_request, query, metric)


def SelectResultFromPeriod(intent_request):
    if intent_request['currentIntent']['slots']['from'] is None and not intent_request['currentIntent']['slots']['resultSet'] is None:
        intent_request['currentIntent']['slots']['from'] = intent_request['currentIntent']['slots']['resultSet']

    query  = DataQuery(intent_request['currentIntent']['slots'])
    metric = DataMetric({
        'metric': 'resultset'
    }, query.query_from)

    return process_query(intent_request, query, metric)

def ShowViewer(intent_request):
    session = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    data_session = get_session(session)

    if data_session is None:
        return close(
            session,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': "I'm sorry, I can't give you the link to the viewer right now..."
            },
            {}
        )
    else:
        return close(
            session,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': 'Sure, you can view the results here: {}'.format(HumanReadable.get_url_to_viewer(data_session.session_id))
            },
            {}
        )

def ShowHelp(intent_request):
    session = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    return close(
        session,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': "Read more about how we can work together here: {}".format(HumanReadable.get_url_to_help())
        },
        {}
    )


def dispatch(intent_request):
    logger.info('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))
    logger.info('dispatch slots={}'.format(intent_request['currentIntent']['slots']))

    intent_name = intent_request['currentIntent']['name']

    if intent_name == 'SelectMetricFromPeriod':
        return selectMetricFromPeriod(intent_request)
    if intent_name == 'SelectBooleanFromPeriod':
        return SelectBooleanFromPeriod(intent_request)
    if intent_name == 'SelectResultFromPeriod':
        return SelectResultFromPeriod(intent_request)
    if intent_name == 'ShowViewer':
        return ShowViewer(intent_request)
    if intent_name == 'Help':
        return ShowHelp(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


def lambda_handler(event, context):
    os.environ['TZ'] = 'America/Los_Angeles'
    time.tzset()
    logger.info('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)


if __name__ == '__main__':
    import sys
    #sys.path.append("/local/lib/python2.7/dist-packages")
    #sys.path.insert(0, "/local/lib/python2.7/dist-packages")
    os.environ['DATABOT_ZD_EMAIL'] = 'm.lundberg@aland.net'
    os.environ['DATABOT_ZD_TOKEN'] = 'mxGXNPQEKGxe7Kxq14mRXzkprZIRSlkwI1Dxx1do'
    os.environ['DATABOT_ZD_SUBDOMAIN'] = 'databotcompany'
    os.environ['DATABOT_VIEWER_ENDPOINT'] = 'http://dataexplorerbot.s3-website-us-east-1.amazonaws.com'

    #print sys.path
    logging.basicConfig()
    if len(sys.argv) > 1:

        json_file = sys.argv[1]
        print "Reading json-file {}".format(json_file)
        with open(json_file, 'r') as json_file:
            test_event_json = json_file.read()

        test_event = json.loads(test_event_json)
        res = lambda_handler(test_event, '')
        print json.dumps(res, indent=4, sort_keys=True)
    else:
        print "Provide json file to test-with."
