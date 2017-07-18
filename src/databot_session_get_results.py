import logging
from aws_helpers import validate_item
from databot_session import DataBot_Session
from databot_handle_input import HumanReadable

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    if not validate_item('session_id', event):
        raise Exception("Not a valid session id.")

    session = DataBot_Session.get(event['session_id'])
    if session == False:
        raise Exception("Not a valid session id.")

    metric = session.get_metric()
    query  = session.get_query()

    if metric == False or query == False:
        raise Exception("Not a valid session id.")

    result = metric.calc_on_query(query)

    ret = {
        'message': '{}'.format(HumanReadable.dataMetricResult(result, query, session.session_id, False)),
        'query': query.toDict(),
        'metric': metric.toDict(),
        'results': result.results
    }

    return ret

if __name__ == '__main__':
    import sys
    import os
    logging.basicConfig()
    os.environ['DATABOT_ZD_EMAIL'] = ''
    os.environ['DATABOT_ZD_TOKEN'] = ''
    os.environ['DATABOT_ZD_SUBDOMAIN'] = ''
    res = lambda_handler({'session_id': '6d3f2794-7541-51ab-9591-71062e6367e7'}, '')
    print res
