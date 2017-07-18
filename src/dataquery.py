import json
import datetime
import time
import os
import dateutil.parser
import logging
from zenpy import Zenpy
from zenpy.lib.api_objects import Ticket, User
import re

logger = logging.getLogger()

# Tries to parse string describing a relative date, and returns it.
# e.g. last 7 days, yesterday, tomorrow, etc.
# TODO This should return start, end date to search from. For better semantic parsing of a period
def parse_period(period):
    if 'yesterday' in period:
        period = '1.5 day' # See above todo, yesterday eqauls 1.5 days is kind of a hack here...
    elif 'tomorrow' in period:
        period = 'next 1 day'
    elif 'today' in period:
        period = '1 day'

    str_to_num = {'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5', 'six': '6', 'seven': '7',
    'eight': '8', 'nine': '9', 'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13'}

    for num in str_to_num:
        period = period.replace(" {} ".format(num), str_to_num[num])

    for match in ['day', 'week', 'month', 'year', 'minute', 'second']:
        if match in period:
            add_delta = False if not 'next' in period else True
            regexp = re.search(r'\d+', period)
            if regexp is None:
                qty = 1
            else:
                qty = int(regexp.group())

            if qty is None:
                qty = 1
            deltaparams = {}

            if match == 'month':
                match = 'day'
                qty = qty * 30
            elif match == 'year':
                match = 'day'
                qty = qty * 365

            deltaparams[match+'s'] = qty
            print deltaparams

            if add_delta:
                date_period_ago = datetime.datetime.now() + datetime.timedelta(**deltaparams)
            else:
                date_period_ago = datetime.datetime.now() - datetime.timedelta(**deltaparams)

            return date_period_ago


    return None

class DataQuery(object):
    filter_to_zenpy = {
        'new': ['status', 'new'],
        'open': ['status', 'open'],
        'pending': ['status', 'pending'],
        'closed': ['status', 'closed'],
        'solved': ['status', 'solved'],
        'hold': ['status', 'hold'],
        #'on-hold': ['status', 'hold'],
        #'low': ['priority', 'low'],
        'low priority': ['priority', 'low'],
        #'medium': ['priority', 'medium'],
        'medium priority': ['priority', 'medium'],
        #'priority': ['priority', 'high'], # TODO is this wise? ... NO!
        #'high': ['priority', 'high'],
        'high priority': ['priority', 'high'],
        'urgent': ['priority', 'urgent'],
        'critical': ['priority', 'urgent'],
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
        'due': 'due_date_between',
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

    def __init__(self, parameters):
        self.zenpy_client = False
        self.filters = []
        self.query_from = False
        self.event = False
        self.period = False
        self.entity = False

        # Go through both filter and betafilter and add each word from them
        for param in ['filter', 'betafilter']:
            for allowed_filter in self.filter_to_zenpy:
                if param in parameters:
                    if (not parameters[param] is None) and (allowed_filter in parameters[param]) and (allowed_filter not in self.filters):
                        self.filters.append(allowed_filter)

        if 'event' in parameters:
            self.event = parameters['event']

        if 'from' in parameters:
            self.query_from = parameters['from']
        elif 'query_from' in parameters:
            self.query_from = parameters['query_from']

        if 'period' in parameters:
            self.period = parameters['period']

            if self.event == False or self.event is None:
                self.event = 'created'

        if 'entity' in parameters:
            self.entity = parameters['entity']

        # TODO This converts input params to lowercase, unsure if it's a good idea to be so defensive...
        for d in self.__dict__:
            if isinstance(self.__dict__[d], basestring):
                self.__dict__[d] = self.__dict__[d].lower()

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

        if self.period != False and self.period != None and parse_period(self.period) is None:
            ret.append({'parameter': 'period', 'value': self.period, 'reason': 'unknown'})

        if self.entity and not self.entity in self.entity_to_zenpy:
            ret.append({'parameter': 'entity', 'value': self.entity, 'reason': 'unknown'})

        if len(self.filters) == 0 and self.event == False and self.entity == False:
            ret.append({'parameter': 'filter', 'value': None, 'reason': 'empty'})

        # Make request invalid if no status filter given without an event. Due to performance reasons
        if self.event == False and (not 'status' in has_filter_type):
            ret.append({'parameter': 'filter', 'value': None, 'reason': 'performance'})
        # Make request invalid if filter on closed/solved without an event. Due to performance reasons
        elif self.event == False and (has_filter_type['status'] == 'closed' or has_filter_type['status'] == 'solved'):
            ret.append({'parameter': 'filter', 'value': has_filter_type['status'], 'reason': 'performance'})

        return ret


    # Simple json serialization
    def toJson(self):
        jsonobj = self.__dict__
        jsonobj['zenpy_client'] = None
        jsonobj['filters'] = self.filters
        return json.dumps(jsonobj)

    def toDict(self):
        obj = self.__dict__
        obj['zenpy_client'] = None
        obj['filters'] = self.filters
        return obj

    # Simple json deserialization
    @staticmethod
    def fromJson(jsonIn):
        params = json.loads(jsonIn)

        if 'filters' in params:
            params['filter'] = " ".join(params['filters'])

        return DataQuery(params)

    def execute(self):
    	# select data via API from
    	#  right endpoint via from
    	#  right time period via period
    	#  filter on entity, filter and betafilter as required
    	# Apply entry = prepare_row(from, entry) for each result entry

        creds = {
            'email' : os.environ['DATABOT_ZD_EMAIL'],
            'token' : os.environ['DATABOT_ZD_TOKEN'],
            'subdomain': os.environ['DATABOT_ZD_SUBDOMAIN']
        }

        zenpy_query = {}

        query_from = self.from_to_zenpy[ self.query_from ]
        zenpy_query[ query_from[0] ] = query_from[1]

        ## Apply filters
        for filter in self.filters:
            if filter in self.filter_to_zenpy:
                f = self.filter_to_zenpy[ filter ]
                zenpy_query[ f[0] ] = f[1]

        ## Create period based on events
        if self.period:
            period_date = parse_period(self.period)
            now         = datetime.datetime.now()

            #event = self.event if self.event != False else 'created' # Done when creating query instead
            if self.event in self.event_to_zenpy:
                event = self.event_to_zenpy[ self.event ]
            else:
                evemt = self.event+"_between"

            if period_date < now:
                zenpy_query[event] = [period_date, now]
            else:
                zenpy_query[event] = [now, period_date]

        # Execute the actual search
        self.zenpy_client = Zenpy(**creds)
        logger.info("Query sent to Zendesk: {}".format(zenpy_query))
        zenpy_search = self.zenpy_client.search(**zenpy_query)

        result = []
        print zenpy_search
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
            #print entry.via.source
            #ret['from_email'] = entry.via.source.from_.address if not entry.via.source.from_ is None else None
            ret['updated'] = entry.updated_at
            ret['created'] = entry.created_at
            ret['subject'] = entry.subject
            ret['priority'] = entry.priority
            ret['type'] = entry.type
            ret['status'] = entry.status
            ret['tags'] = entry.tags

            #metrics = self.zenpy_client.tickets.metrics(entry.id)
            #ret['replies'] = metrics.replies

            #if not metrics.assigned_at is None:
            #    assignment_time = datetime.datetime.now() - datetime.datetime.strptime(metrics.assigned_at, '%Y-%m-%dT%H:%M:%SZ')
            #    ret['assignment_time'] = assignment_time.total_seconds()

            #satisfaction_ratings = {
                #'offered': False, 'unoffered': False,
            #    'bad': 0, 'good': 1}
            #if entry.satisfaction_rating.score in satisfaction_ratings:
            #    ret['satisfaction_rating'] = satisfaction_ratings[ entry.satisfaction_rating.score ]

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
    ret['result'] = ret['count']
    #if not ret['result']:
    #    ret['result'] = [entry]
    #else:
    #    ret['result'].append(entry)
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

    def __init__(self, parameters, query_from):
        self.metric = False
        self.value = False
        self.query_from = False

        if 'metric' in parameters:
            self.metric = parameters['metric']

        if 'value' in parameters:
            self.value = parameters['value']

        # Assume count if nothing else given
        if not self.value:
            logger.info("No value given to calcuate metric on, assuming count.")
            self.value = 'count'

        self.query_from = query_from

        # TODO This converts input params to lowercase, unsure if it's a good idea to be so defensive...
        for d in self.__dict__:
            if isinstance(self.__dict__[d], basestring):
                self.__dict__[d] = self.__dict__[d].lower()

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

        return DataMetricResult(self.metric, self.value, ret['result'], ret['count'], '', ret['entry'], results)

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

    def toDict(self):
        return self.__dict__

    @staticmethod
    def fromJson(jsonIn):
        params = json.loads(jsonIn)
        return DataMetric(params, params['query_from'])


class DataMetricResult(object):
    def __init__(self, metric, value, result, count, query_from, entry, results):
        self.metric = metric
        self.value = value
        self.result = result
        self.count = count
        self.query_from = query_from
        self.entry = entry
        self.results = results

    def toJson(self):
        obj = self.__dict__
        obj['results'] = None
        return json.dumps(obj)

    @staticmethod
    def fromJson(jsonIn):
        params = json.loads(jsonIn)
        return DataMetricResult(**params)
