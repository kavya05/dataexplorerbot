import csv
import os
import json
from .context import lambda_function

import unittest

class TestQueries(unittest.TestCase):
    queries = []

    def setUp(self):
        path = os.path.dirname(os.path.realpath(__file__))+'/queries.csv'
        print "Reading from {}".format(path)
        #Metric	Value	Filter	BetaFilter	Event	From	Period	Entity	Grouped	ResultSet	Returns	Intent
        with open(path, 'rb') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
            entry = {}
            for row in spamreader:
                entry = {}
                c = 0

                for key in ['metric','value','filter','betafilter','event','from','period','entity','grouped','resultSet','returns','intent','response','comment','skip','id']:
                    if c < len(row):
                        val = row[c]
                        entry[key] = val if val != "" else None
                        c += 1

                if 'skip' in entry and entry['skip'] == '1':
                    print "Skipping row..."
                else:
                    self.queries.append(entry)

        self.queries.pop(0)

    def testQueries(self):
        for query in self.queries:
            self.failUnless('intent' in query)

            event = {
              "currentIntent": {
                "slots": {
                  "metric": query['metric'],
                  "value": query['value'],
                  "filter": query['filter'],
                  "betafilter": query['betafilter'],
                  "from": query['from'],
                  "resultSet": query['resultSet'],
                  "event": query['event'],
                  "period1": query['period']
                },
                "name": query['intent'],
                "confirmationStatus": "None"
              },
              "bot": {
                "alias": "$LATEST",
                "version": "$LATEST",
                "name": "DataBot"
              },
              "userId": "MatsL",
              "invocationSource": "",
              "invocationSource1": "DialogCodeHook",
              "outputDialogMode": "Text",
              "messageVersion": "1.0",
              "sessionAttributes": {}
            }

            context = {}

            res = lambda_function.lambda_handler(event, context)

            expectedResponse = query['response']
            realResponse = res['dialogAction']['message']['content']
            #print expectedResponse , realResponse, res
            print "Testing ID:{} -- {}".format(query['id'], query)
            self.assertTrue(expectedResponse in realResponse, "Response not as expected: {} != {}".format(expectedResponse, realResponse))

def main():
    unittest.main()

if __name__ == '__main__':
    main()
