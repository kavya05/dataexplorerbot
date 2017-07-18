from aws_helpers import v4_createPresignedURL
from aws_helpers import validate_item
import sys
sys.path.insert(0, "/local/lib/python2.7/dist-packages")
import json
import os
import time
import logging
import boto3
from databot_session import DataBot_Session
from databot_handle_input import HumanReadable

logger = logging.getLogger()
client = boto3.client('iot-data')

def push_to_mqtt(topic, rows):
    for row in rows:
        response = client.publish(topic=topic, qos=0, payload=row)

def publish_query(session_id, results):
    session = DataBot_Session.get(session_id)
    metric = session.get_metric()
    query  = session.get_query()
    result = session.get_result()

    if metric == False or query == False:
        raise Exception("Not a valid session id.")

    runseq = time.time()
    rows = []

    rows.append( json.dumps({'type':'start','runseq':runseq}) )
    rows.append( json.dumps({'type':'message','runseq':runseq, 'value': '{}'.format(HumanReadable.dataMetricResult(result, query, session_id, False))} ) )
    rows.append( json.dumps({'type':'query','runseq':runseq, 'value': query.toDict()}) )
    rows.append( json.dumps({'type':'metric','runseq':runseq, 'value': metric.toDict()}) )

    for entry in results:
        rows.append( json.dumps({'type':'entry', 'runseq':runseq, 'value': entry}) )

    rows.append( json.dumps({'type':'end','runseq':runseq}) )

    topic = "databot/session/"+session_id
    push_to_mqtt(topic, rows)

def notify_publish(session_id):
    session = DataBot_Session.get(session_id)

    runseq = time.time()
    rows = []

    rows.append( json.dumps({'type':'start','runseq':runseq}) )

    topic = "databot/session/"+session_id
    push_to_mqtt(topic, rows)

def lambda_handler(event, context):
    if not validate_item('session_id', event):
        raise Exception('Not a valid session_id')

    if validate_item('results', event):
        logger.info('Publishing a resultSet')
        publish_query(event['session_id'], event['results'])
    else:
        logger.info('Notifying about upcoming publish of resultSet')
        notify_publish(event['session_id'])

    return True

if __name__ == '__main__':
    os.environ['DATABOT_MQTT_HOST'] = 'a7aevuun65t6z.iot.us-east-1.amazonaws.com'
    os.environ['DATABOT_MQTT_REGION'] = 'us-east-1'
    import sys, json
    res = lambda_handler({
        'session_id':'6d3f2794-7541-51ab-9591-71062e6367e7',
        'results':
            [{"age": 2566.302037, "ticket_id": 113877}, {"age": 6830.304217, "ticket_id": 113871}]
    }, {})
    print json.dumps(res)
