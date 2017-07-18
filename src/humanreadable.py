import logging
import os
from aws_helpers import pretty_seconds

logger = logging.getLogger()

# Class to take dataobject and convert them to human readable strings.
# Effectivly the UI.
# TODO Would probably be best as function in this file instead of a static class like below...
class HumanReadable(object):
    @staticmethod
    def get_url_to_viewer(session_id):
        if 'DATABOT_VIEWER_ENDPOINT' in os.environ:
            return "{}/#{}".format(os.environ['DATABOT_VIEWER_ENDPOINT'], session_id)

        return ''

    @staticmethod
    def get_url_to_help():
        if 'DATABOT_VIEWER_ENDPOINT' in os.environ:
            return "{}/help.html".format(os.environ['DATABOT_VIEWER_ENDPOINT'])

        return '';

    @staticmethod
    def DataQuery_validate(invalid_query, invalid_metric):
        logger.info('invalid_query/invalid_metric={}/{}'.format(invalid_query, invalid_metric))

        message = ["Sorry, I can't answer your question... "]
        for invalid_slot in invalid_query:
            if invalid_slot['parameter'] == 'value' and invalid_slot['value'] != False:
                if invalid_slot['reason'] == 'contradiction':
                    message.append("Getting both {} and {} doesn't make sense to me.".format(invalid_slot['value'], invalid_slot['contradiction_value']))
                else:
                    message.append("What {} as {}?".format(invalid_slot['parameter'], invalid_slot['value']))
            elif invalid_slot['parameter'] == 'filter' and invalid_slot['value'] != False:
                if invalid_slot['reason'] == 'contradiction':
                    message.append("Filter on both {} and {} doesn't make sense to me.".format(invalid_slot['value'], invalid_slot['contradiction_value']))
                elif invalid_slot['reason'] == 'empty':
                    message.append("You need to provide a filter, e.g. 'open', 'closed'.")
                elif invalid_slot['reason'] == 'performance':
                    #message.pop()
                    message.append("You question would take too much time to process. Please provide a period, e.g. 'during last 2 weeks' to narrow down result")
                else:
                    message.append("I cannot filter on {}".format(invalid_slot['value']))
            elif invalid_slot['parameter'] == 'period':
                message.append("I do not understand the period you gave me: '{}'.".format(invalid_slot['value']))
            else:
                #if invalid_slot['parameter']
                message.append("I do not understand '{}'".format(invalid_slot['value']))
                message.append("UNKNOWN QUERY: {}".format(invalid_slot))

        for invalid_slot in invalid_metric:
            if invalid_slot['parameter'] == 'from':
                if invalid_slot['value'] == False or invalid_slot['value'] == None:
                    message.append("I'm not sure what you want kind of data you want.")
                else:
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
    def eventperiod(event, period):
        if not (period and event):
            return ""

        verb = 'were'
        if 'next' in period or 'tomorrow' in period:
            verb = 'are'

        if period in ['tomorrow', 'yesterday']:
            return "which {} {} {}".format(verb, event, period)
        else:
            return "which {} {} during {}".format(verb, event, period)


    @staticmethod
    def dataMetricResult(result, query, session_id, include_viewer_link):
        res = result.result

        if result.metric == 'exists' or result.metric == 'resultset' or (result.value == 'count'):
            if res:
                ret = "I found {}".format(result.count)
            else:
                ret = "Sorry, I didn't find any"

            ret = "{} {} {} {}".format(ret, " ".join(query.filters), query.query_from, HumanReadable.eventperiod(query.event, query.period))

            if include_viewer_link and res and result.metric == 'resultset':
                ret = "{}. You can view them here: {}".format(ret, HumanReadable.get_url_to_viewer(session_id))

            return ret
        else:
            if result.count > 0:
                metric_hr = result.metric.title()
                value_hr  = result.value
                result_hr = res

                if result.value == 'satisfaction_rating':
                    value_hr = 'rating'
                    if not result_hr:
                        return "{} {} couldn't be determined for {} {} {} found".format(metric_hr, value_hr, result.count, " ".join(query.filters), query.query_from)
                    else:
                        result_hr = "{:.1%}".format(res)

                if result.value == 'age':
                    result_hr = pretty_seconds(res)

                return "{} {} is {} for {} {} {} found {}".format(metric_hr, value_hr, result_hr, result.count, " ".join(query.filters), query.query_from, HumanReadable.eventperiod(query.event, query.period))
            else:
                ret = "Sorry, I didn't find any {} {} {}".format(" ".join(query.filters), query.query_from, HumanReadable.eventperiod(query.event, query.period))

                return ret
