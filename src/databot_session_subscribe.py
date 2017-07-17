import sys, os, base64, datetime, hashlib, hmac, urllib
from aws_helpers import v4_createPresignedURL
from aws_helpers import validate_item
from databot_session import DataBot_Session

def lambda_handler(event, context):
    if not validate_item('session_id', event) or not DataBot_Session.get(event['session_id']):
        return {'success': False, 'message':"Not a valid session id."}

    url = v4_createPresignedURL(
        'GET',
        os.environ['DATABOT_MQTT_HOST'],
        '/mqtt',
        'iotdevicegateway',
        '',
        os.environ['DATABOT_ACCESS_KEY_ID'],
        os.environ['DATABOT_SECRET_ACCESS_KEY'],
        'wss',
        60,
        os.environ['DATABOT_MQTT_REGION']
    )

    return {'success': True, 'url': url}

if __name__ == '__main__':
    os.environ['DATABOT_MQTT_HOST'] = 'mqtt_host'
    os.environ['DATABOT_ACCESS_KEY_ID'] = 'access_key'
    os.environ['DATABOT_SECRET_ACCESS_KEY'] = 'secret_key'
    os.environ['DATABOT_MQTT_REGION'] = 'region'
    import sys, json
    res = lambda_handler({},{})
    print json.dumps(res)
