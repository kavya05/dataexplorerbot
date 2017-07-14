### 1. Compile tests from Excel
### 2. Intents SelectMetricResultRef, SelectBooleanFromPeriod, SelectResultFromPeriod [/]
### 3. Implement "complete" query filtering, e.g. support for form other than ticket [/]
### 4. Test that this can be run on lambda
### 5. Eval if offline storage of tickets are required for performance reasons



import json
import datetime
import time
import os
import dateutil.parser
import logging
from dataquery import DataQuery
from dataquery import DataMetric
#import dateparser

logger = logging.getLogger()
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)
#logger.setLevel(logging.WARN)


class HumanReadable(object):
    @staticmethod
    def DataQuery_validate(invalid_query, invalid_metric):
        logger.info('invalid_query/invalid_metric={}/{}'.format(invalid_query, invalid_metric))

        message = ["Sorry, I don't quite understand you know... "]
        for invalid_slot in invalid_query:
            if invalid_slot['parameter'] == 'value' and invalid_slot['value'] != False:
                if invalid_slot['reason'] == 'contradiction':
                    message.append("Getting both {} and {} doesn't make sense to me.".format(invalid_slot['value'], invalid_slot['contradiction_value']))
                else:
                    message.append("What {} as {}?".format(invalid_slot['parameter'], invalid_slot['value']))
            elif invalid_slot['parameter'] == 'filter' and invalid_slot['value'] != False:
                if invalid_slot['reason'] == 'contradiction':
                    message.append("Filter on both {} and {} doesn't make sense to me.".format(invalid_slot['value'], invalid_slot['contradiction_value']))
                else:
                    message.append("I cannot filter on {}".format(invalid_slot['value']))
            else:
                message.append("UNKNOWN QUERY: {}".format(invalid_slot))

        for invalid_slot in invalid_metric:
            if invalid_slot['parameter'] == 'from':
                message.append("I cannot get {}".format(invalid_slot['value']))
            elif invalid_slot['parameter'] == 'value' and invalid_slot['value'] != False:
                if invalid_slot['reason'] == 'contradiction':
                    message.append("Getting {} of {} doesn't make sense to me.".format(invalid_slot['value'], invalid_slot['contradiction_value']))
                else:
                    message.append("I can't get the {} {}".format(invalid_slot['parameter'], invalid_slot['value']))
            else:
                message.append("UNKNOWN METRIC: {}".format(invalid_slot))

        return " ".join(message)

    @staticmethod
    def dataMetricResult(result, query):
        res = result.result

        if result.metric == 'exists':
            if res:
                return "Yes, there are {}".format(result.count)
            else:
                return "No, sorry..."

        elif result.metric == 'resultset':
            if res:
                max_show = 5
                ret_str = "I found {} {} {}".format(len(res), " ".join(query.filters), query.query_from)

                if max_show < len(result.result):
                    ret_str += " (showing {} first)".format(max_show)

                ret_str += ": "

                for entry in result.result[0:max_show]:
                    ret_str += "{} ".format(entry['ticket_id'])

                return ret_str
            else:
                return "There are no such elemnts"
        else:
            if result.count == 0:
                return "Sorry, I didn't find any {} {}".format(" ".join(query.filters), query.query_from)
            else:
                metric_hr = result.metric.title()
                value_hr  = result.value
                result_hr = res

                if result.value == 'satisfaction_rating':
                    value_hr = 'rating'
                    if not result_hr:
                        return "{} {} couldn't be determined for {} {} {} found".format(metric_hr, value_hr, result.count, " ".join(query.filters), query.query_from)
                    else:
                        result_hr = "{:.1%}".format(res)
                    #res =
                elif result.value == 'count':
                    return "I found {} {} {}".format(result_hr, " ".join(query.filters), query.query_from)

                if result.value == 'age':
                    result_hr = pretty_seconds(res)

                return "{} {} is {} for {} {} {} found".format(metric_hr, value_hr, result_hr, result.count, " ".join(query.filters), query.query_from)




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


# --- Helper Functions ---

def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def get_day_difference(later_date, earlier_date):
    later_datetime = dateutil.parser.parse(later_date).date()
    earlier_datetime = dateutil.parser.parse(earlier_date).date()
    return abs(later_datetime - earlier_datetime).days


def add_days(date, number_of_days):
    new_date = dateutil.parser.parse(date).date()
    new_date += datetime.timedelta(days=number_of_days)
    return new_date.strftime('%Y-%m-%d')


def build_validation_result(isvalid, violated_slot, message_content):
    return {
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


# Thanks, https://stackoverflow.com/questions/1551382/user-friendly-time-format-in-python
def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time,datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff / 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff / 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff / 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff / 30) + " months ago"
    return str(day_diff / 365) + " years ago"

def pretty_seconds(sec):
    second_diff = int(sec)
    day_diff = int(sec / (24*3600))

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "seconds"
        if second_diff < 60:
            return str(second_diff) + " seconds"
        if second_diff < 120:
            return "a minute"
        if second_diff < 3600:
            return str(second_diff / 60) + " minutes"
        if second_diff < 7200:
            return "an hour"
        if second_diff < 86400:
            return str(second_diff / 3600) + " hours"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days"
    if day_diff < 31:
        return str(day_diff / 7) + " weeks"
    if day_diff < 365:
        return str(day_diff / 30) + " months"
    return str(day_diff / 365) + " years"


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


# filter, metric, from, period
def selectMetricFromPeriod(intent_request):
    session = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    query  = DataQuery(intent_request['currentIntent']['slots'])
    metric = DataMetric(intent_request['currentIntent']['slots'], query.query_from)

    session['current_query'] = query.toJson()
    session['current_metric'] = metric.toJson()

    logger.info('query/metric={}/{}'.format(query.toJson(), metric.toJson()))

    invalid = request_is_invalid(query, metric, intent_request)
    if invalid != False:
        return invalid

    if intent_request['invocationSource'] == 'DialogCodeHook':
        return delegate(session, intent_request['currentIntent']['slots'])

    result = metric.calc_on_query(query)

    #session['current_query']  = query
    session['current_result'] = result.toJson()

    return close(
        session,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': '{} '.format(HumanReadable.dataMetricResult(result, query))
        },
        {}
    )

def SelectBooleanFromPeriod(intent_request):
    session = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    query  = DataQuery(intent_request['currentIntent']['slots'])
    metric = DataMetric({
        'metric': 'exists'
    }, query.query_from)

    session['current_query'] = query.toJson()
    session['current_metric'] = metric.toJson()

    invalid = request_is_invalid(query, metric, intent_request)
    if invalid != False:
        return invalid

    if intent_request['invocationSource'] == 'DialogCodeHook':
        return delegate(session, intent_request['currentIntent']['slots'])

    result = metric.calc_on_query(query)

    logger.info('query/metric={}/{}'.format(query.toJson(), metric.toJson()))

    return close(
        session,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': '{} '.format(HumanReadable.dataMetricResult(result, query))
        },
        {}
    )

def SelectResultFromPeriod(intent_request):
    session = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    if intent_request['currentIntent']['slots']['from'] is None and not intent_request['currentIntent']['slots']['resultSet'] is None:
        intent_request['currentIntent']['slots']['from'] = intent_request['currentIntent']['slots']['resultSet']

    query  = DataQuery(intent_request['currentIntent']['slots'])
    metric = DataMetric({
        'metric': 'resultset'
    }, query.query_from)

    session['current_query'] = query.toJson()
    session['current_metric'] = metric.toJson()

    invalid = request_is_invalid(query, metric, intent_request)
    if invalid != False:
        return invalid

    if intent_request['invocationSource'] == 'DialogCodeHook':
        return delegate(session, intent_request['currentIntent']['slots'])


    result = metric.calc_on_query(query)

    logger.info('query/metric={}/{}'.format(query.toJson(), metric.toJson()))

    return close(
        session,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': '{} '.format(HumanReadable.dataMetricResult(result, query))
        },
        {}
    )

# --- Intents ---


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.info('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))
    logger.info('dispatch slots={}'.format(intent_request['currentIntent']['slots']))

    intent_name = intent_request['currentIntent']['name']

    if intent_name == 'SelectMetricFromPeriod':
        return selectMetricFromPeriod(intent_request)
    if intent_name == 'SelectBooleanFromPeriod':
        return SelectBooleanFromPeriod(intent_request)
    if intent_name == 'SelectResultFromPeriod':
        return SelectResultFromPeriod(intent_request)


    raise Exception('Intent with name ' + intent_name + ' not supported')


# --- Main handler ---


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.info('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)


if __name__ == '__main__':
    import sys
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
