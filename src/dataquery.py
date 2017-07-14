import json
import datetime
import time
import os
import dateutil.parser
import logging
from zenpy import Zenpy
from zenpy.lib.api_objects import Ticket, User

logger = logging.getLogger()

class DataQuery(object):
    zenpy_client = False
    filters = []
    query_from = False
    event = False
    period = False
    entity = False

    filter_to_zenpy = {
        'new': ['status', 'new'],
        'open': ['status', 'open'],
        'pending': ['status', 'pending'],
        'closed': ['status', 'closed'],
        'solved': ['status', 'solved'],
        'on-hold': ['status', 'on-hold'],
        'low': ['priority', 'low'],
        #'low priority': ['priority', 'low'],
        'medium': ['priority', 'medium'],
        #'medium priority': ['priority', 'medium'],
        #'priority': ['priority', 'high'], # TODO is this wise? ... NO!
        'high': ['priority', 'high'],
        #'high priority': ['priority', 'high'],
        'urgent': ['priority', 'urgent'],
        'critical': ['priority', 'critical'],
    }

    filter_to_postprocess = {
        #one-touch
        'oldest': ['age', 'max'],
        'newest': ['age', 'min'],
        'youngest': ['age', 'min'],
        'most recent': ['age', 'min']
        #Newest	Youngest, Most recent
    }

    event_to_zenpy = {
        'deleted': 'deleted_between',
        'reopened': 'reopened_between',
        'created': 'created_between',
        'added': 'created_between',
        'opened': 'created_between',
        'solved': 'solved_between',
        'closed': 'closed_between',
        'updated': 'updated_between',
    }

    from_to_zenpy = {
        'tickets': ['type', 'ticket'],
        'issues': ['type', 'ticket'],
        'agents': ['type', 'agent'],
        'organizations': ['type', 'organization'],
        'users': ['type', 'user'],
        'incidents': ['ticket_type', 'incident'],
        'problems': ['ticket_type', 'problem'],
        'tasks': ['ticket_type', 'task'],
        'questions': ['ticket_type', 'question']
    }

    entity_to_zenpy = {
    }

    #EVENTS

#    METRICS
    #Metrics
    #Average
    #Number of
    #Median
    #Min
    #Max
#    Most
#    Percentage
#    Least
#    Best
    """
        VALUES
        Age
        (Count)
        First reply time
        Satisfaction Rating
        Active (??)
        Assignment time

        GROUPED
        Ticket status
        Agent
        Group
        Channel
        Organization
        Customer
        Brand
        Priority
        Status
        Ticket type

        FROM
        Tickets
        Agents
        Those tickets
        These tickest
        Of these
        Incident
        Question
        Problem
        Task

        ENITITY
        Brand X
        Customer X
        Channel X
        Group X
        Organization X
        it
        them
        these
        those
    """

    def __init__(self, parameters):
        # Go through both filter and betafilter and add each word from them
        logger.info("Init DataQuery")
        for param in ['filter', 'betafilter']:
            for allowed_filter in self.filter_to_zenpy:
                logger.info("Looking at allowed_filter "+allowed_filter)
                if param in parameters:
                    logger.info("Looking at parameter "+param)
                    logger.info("{}/{}/{}".format(parameters[param], allowed_filter in parameters[param], allowed_filter not in self.filters))
                    if (not parameters[param] is None) and (allowed_filter in parameters[param]) and (allowed_filter not in self.filters):
                        self.filters.append(allowed_filter)
                #for param_word in parameters[param].split(" "):
                #    if param_word and not param_word in self.filters:
        print self.filters
        if 'event' in parameters:
            self.event = parameters['event']

        if 'from' in parameters:
            self.query_from = parameters['from']

        if 'period' in parameters:
            self.period = parameters['period']

        if 'entity' in parameters:
            self.entity = parameters['entity']

    def validate(self):
        ret = []
        has_filter_type = {}
        for param in self.filters:
            if not param in self.filter_to_zenpy and not param in self.filter_to_postprocess:
                ret.append({'parameter': 'filter', 'value': param, 'reason': 'unknown'})

            # Check if filter with same type alrady exists => contradiction!
            if param in self.filter_to_zenpy:
                filter_type = self.filter_to_zenpy[param][0]
                if filter_type in has_filter_type:
                    ret.append({'parameter': 'filter', 'value': param, 'reason': 'contradiction', 'contradiction_value': has_filter_type[filter_type]})
                else:
                    has_filter_type[ filter_type ] = param

        if self.event and not self.event in self.event_to_zenpy:
            ret.append({'parameter': 'event', 'value': self.event, 'reason': 'unknown'})

        if self.query_from and not self.query_from in self.from_to_zenpy:
            ret.append({'parameter': 'from', 'value': self.event, 'reason': 'unknown'})

        ## TODO Add validation of self.period

        if self.entity and not self.entity in self.entity_to_zenpy:
            ret.append({'parameter': 'entity', 'value': self.entity, 'reason': 'unknown'})

        return ret


    # Simple json serialization
    def toJson(self):
        jsonobj = self.__dict__
        jsonobj['zenpy_client'] = None
        jsonobj['filters'] = self.filters
        return json.dumps(jsonobj)

    # Simple json deserialization
    @staticmethod
    def fromJson(json):
        params = json.loads(json)
        params['filter'] = params['filter'].join(" ")
        return DataQuery(params)
        #query = {
        #    'filter':     intent_request['currentIntent']['slots']['filter'] if 'filter' in intent_request['currentIntent']['slots'] is not None else False,
        #    'betafilter': intent_request['currentIntent']['slots']['betafilter'] if 'betafilter' in intent_request['currentIntent']['slots'] is not None else False,
        #    'event':      intent_request['currentIntent']['slots']['event'] if 'event' in intent_request['currentIntent']['slots'] is not None else False,
        #    'from':       intent_request['currentIntent']['slots']['from'] if 'from' in intent_request['currentIntent']['slots'] is not None else False,
        #    'period':     intent_request['currentIntent']['slots']['period'] if 'period' in intent_request['currentIntent']['slots'] is not None else False,
        #    'entity':     intent_request['currentIntent']['slots']['entity'] if 'entity' in intent_request['currentIntent']['slots'] is not None else False,
        #}
        #self.make = make
        #self.model = model

    def execute(self):
    	# select data via API from
    	#  right endpoint via from
    	#  right time period via period
    	#  filter on entity, filter and betafilter as required
    	# Apply entry = prepare_row(from, entry) for each result entry

        creds = {
            'email' : 'mats.lundberg@carus.com',
            'token' : 'WXXzUFmJAJ4wPFIlrV1vcbdha40hizwR1uvYsfjM',
            'subdomain': 'caruspbs'
        }

        zenpy_query = {}

        print self

        query_from = self.from_to_zenpy[ self.query_from ]
        zenpy_query[ query_from[0] ] = query_from[1]

        ## Apply filters
        for filter in self.filters:
            if filter in self.filter_to_zenpy:
                f = self.filter_to_zenpy[ filter ]
                zenpy_query[ f[0] ] = f[1]

        ## Create period based on events
        if self.period:
            period_date = dateparser.parse(self.period.replace("last", "")+" ago")
            now         = datetime.datetime.now()

            if period_date < now:
                zenpy_query[self.event+'_between'] = [period_date, now]
            else:
                zenpy_query[self.event+'_between'] = [now, period_date]

        # Execute the actual search
        self.zenpy_client = Zenpy(**creds)
        zenpy_search = self.zenpy_client.search(**zenpy_query)

        result = []
        for ticket in zenpy_search:
            result.append(self.prepare_row(self.query_from, ticket))

        # Apply post process filters, gettin oldest, newest entry etc.
        for filter in self.filters:
            if filter in self.filter_to_postprocess:
                f = self.filter_to_postprocess[ filter ]
                metric = DataMetric({
                    'value': f[0],
                    'metric': f[1]
                }, self.query_from)
                res = metric.calc_on_resultSet(result)

                if res.entry:
                    result = [res.entry]
                elif isinstance(res.result, list):
                    result = res.result


        return result

    def prepare_row(self, frm, entry):
        ret = {}
        #if frm == 'tickets':
        #print entry
        if isinstance(entry, Ticket):
            age = datetime.datetime.now() - datetime.datetime.strptime(entry.created_at, '%Y-%m-%dT%H:%M:%SZ')
            ret['age'] = age.total_seconds()
            ret['ticket_id'] = entry.id

            #metrics = self.zenpy_client.tickets.metrics(entry.id)
            #ret['replies'] = metrics.replies

            #if not metrics.assigned_at is None:
            #    assignment_time = datetime.datetime.now() - datetime.datetime.strptime(metrics.assigned_at, '%Y-%m-%dT%H:%M:%SZ')
            #    ret['assignment_time'] = assignment_time.total_seconds()

            satisfaction_ratings = {
                #'offered': False, 'unoffered': False,
                'bad': 0, 'good': 1}
            if entry.satisfaction_rating.score in satisfaction_ratings:
                ret['satisfaction_rating'] = satisfaction_ratings[ entry.satisfaction_rating.score ]

        return ret

def calc_count(entry, field, ret):
    ret['count']  = ret['count'] + 1 if 'count' in ret else 1
    ret['result'] = ret['count']
    return ret

def calc_exists(entry, field, ret):
    ret['count']  = ret['count'] + 1 if 'count' in ret else 1
    ret['result'] = True
    return ret

def calc_resultset(entry, field, ret):
    ret['count']  = ret['count'] + 1 if 'count' in ret else 1
    if not ret['result']:
        ret['result'] = [entry]
    else:
        ret['result'].append(entry)
    return ret

def calc_average(entry, field, ret):
    ret['count'] = ret['count'] + 1 if 'count' in ret else 1

    # Do not include entry in avg calculation if field doesn't exist
    if field in entry:
        ret['average_count'] = ret['average_count'] + 1 if 'average_count' in ret else 1

        old_average = ret['result'] if 'result' in ret else 0
        current_cnt = ret['average_count']

        ret['result'] = (old_average * ((current_cnt-1) / current_cnt) + (entry[field] / current_cnt))

    return ret

def calc_max(entry, field, ret):
    if 'result' not in ret:
        ret['result'] = entry[field]
        ret['entry'] = entry
    else:
        if entry[field] > ret['result']:
            ret['result'] = entry[field]
            ret['entry'] = entry

    return ret

def calc_min(entry, field, ret):
    if 'result' not in ret:
        ret['result'] = entry[field]
        ret['entry'] = entry
    else:
        if entry[field] < ret['result']:
            ret['result'] = entry[field]
            ret['entry'] = entry

    return ret

def calc_notsupported(entry, field, ret):
    return ret

# --- Helpers that build all of the responses ---
class DataMetric(object):
    metric_funcs = {
        'average': calc_average,
        'median': calc_notsupported,
        'min': calc_min,
        'max': calc_max,
        'count': calc_count,
        'many': calc_count,
        'number of': calc_count,
        'most': calc_notsupported,
        'percentage': calc_notsupported,
        'least': calc_notsupported,
        'best': calc_notsupported,
        'exists': calc_exists,
        'resultset': calc_resultset,
    }

    allowed_values = {
        'tickets': {
            'age', 'count'#, 'replies', 'assignment time'
            #'satisfaction rating': 'satisfaction_rating',
        },
        'issues': {},
        'agents': {},
        'organizations': {},
        'users': {},
        'incidents': {
            'age', 'count'#, 'replies', 'assignment time'
            #'satisfaction rating': 'satisfaction_rating',
        },
        'problems': {
            'age', 'count'#, 'replies', 'assignment time'
            #'satisfaction rating': 'satisfaction_rating',
        },
        'tasks': {
            'age', 'count'#, 'replies', 'assignment time'
            #'satisfaction rating': 'satisfaction_rating',
        },
        'questions': {
            'age', 'count'#, 'replies', 'assignment time'
            #'satisfaction rating': 'satisfaction_rating',
        },
    }

    metric = False
    value = False
    query_from = False

    def __init__(self, parameters, query_from):
        if 'metric' in parameters:
            self.metric = parameters['metric']

        if 'value' in parameters:
            self.value = parameters['value']

        # Assume count if nothing else given
        if not self.value:
            logger.info("No value given to calcuate metric on, assuming count.")
            self.value = 'count'

        self.query_from = query_from

    def _calc(self, entry, ret):
        if self.metric:
            return self.metric_funcs[ self.metric ](entry, self.value, ret)
        else:
            logger.info('No metric set! {}/{}/{}'.format(self.metric, self.value, entry))
            return ret

    def calc_on_query(self, query):
        results = query.execute()
        return self.calc_on_resultSet(results)

    def calc_on_resultSet(self, results):
        ret = {'result': False, 'count': 0, 'entry': False}
        for entry in results:
            ret = self._calc(entry, ret)

        #print ret
        return DataMetricResult(self.metric, self.value, ret['result'], ret['count'], '', ret['entry'])

    def validate(self):
        ret = []

        if not self.query_from in self.allowed_values:
            ret.append({'parameter': 'from', 'value': self.query_from, 'reason': 'unknown'})
        elif not self.value in self.allowed_values[self.query_from]:
            ret.append({'parameter': 'value', 'value': self.value, 'reason': 'unknown'})

        if not self.metric in self.metric_funcs:
            ret.append({'parameter': 'metric', 'value': self.metric, 'reason': 'unknown'})

        return ret

    def toJson(self):
        return json.dumps(self.__dict__)


class DataMetricResult(object):
    metric = False
    value = False
    result = False
    count = False
    query_from = False
    entry = False

    def __init__(self, metric, value, result, count, query_from, entry):
        self.metric = metric
        self.value = value
        self.result = result
        self.count = count
        self.query_from = query_from
        self.entry = entry

    def toJson(self):
        return json.dumps(self.__dict__)
