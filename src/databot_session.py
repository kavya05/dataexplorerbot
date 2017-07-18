import logging
import uuid
import sys
sys.path.insert(0, "/local/lib/python2.7/dist-packages")
import boto3
import json
from dataquery import DataMetric, DataQuery, DataMetricResult

logger = logging.getLogger()

dynamodb_client = boto3.resource('dynamodb')
dynamodb_table = dynamodb_client.Table('databot_sessions')

class DataBot_Session(object):
    def __init__(self, session_id):
        self.item = False
        self.session_id = session_id

    @staticmethod
    def create():
        session_id = "{}".format(uuid.uuid4())

        item = {
            'session_id': {'S':session_id}
        }

        try:
            dynamodb_table.put_item(Item={'session_id': session_id})
        except Exception, e:
            session_id = False
            logger.warn("Failed to create session: {}".format(e))
        else:
            return DataBot_Session(session_id)

    @staticmethod
    def get(session_id):
        item = {
            'session_id': {'S':session_id}
        }

        try:
            print ""#self.dynamodb_table.put_item(Item={'session_id': session_id})
        except Exception, e:
            session_id = False
            logger.warn("Failed to create session: {}".format(e))
        else:
            return DataBot_Session(session_id)

    def update(self, query, metric, result):
        key = {
            'session_id': self.session_id,
        }

        res = True

        try:
            dynamodb_table.update_item(
                Key = key,
                UpdateExpression = 'set session_query = :q, session_metric = :m, session_result = :r',
                ExpressionAttributeValues = {
                    ':q': query.toJson(),
                    ':m': metric.toJson(),
                    ':r': result.toJson()
                }
            )
        except Exception, e:
            res = False
            logger.warn("Failed to update session: {}".format(e))

        return res

    def _get_item(self, session_id):
        key = {
            'session_id': self.session_id
        }

        try:
            res = dynamodb_table.get_item(Key = key)
            self.item = res['Item']
        except Exception, e:
            logger.warn("Failed to get query: {}".format(e))
            return False
        else:
            return self.item

    def get_query(self):
        if self.item == False:
            item = self._get_item(self.session_id)
        else:
            item = self.item

        if item == False:
            return False

        return DataQuery.fromJson(item['session_query']) if 'session_query' in item else False

    def get_result(self):
        if self.item == False:
            item = self._get_item(self.session_id)
        else:
            item = self.item

        if item == False:
            return False

        return DataMetricResult.fromJson(item['session_result']) if 'session_result' in item else False

    def get_metric(self):
        if self.item == False:
            item = self._get_item(self.session_id)
        else:
            item = self.item

        if item == False:
            return False

        return DataMetric.fromJson(item['session_metric']) if 'session_metric' in item else False
