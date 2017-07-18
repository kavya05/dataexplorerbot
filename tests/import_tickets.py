from zenpy import Zenpy
from zenpy.lib.api_objects import Ticket
import sys
sys.path.insert(0, "/local/lib/python2.7/dist-packages")
import os
import logging
import datetime
from faker import Faker
from random import randint

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def import_tickets(tickets):
    creds = {
        'email' : os.environ['DATABOT_ZD_EMAIL'],
        'token' : os.environ['DATABOT_ZD_TOKEN'],
        'subdomain': os.environ['DATABOT_ZD_SUBDOMAIN']
    }
    zenpy_client = Zenpy(**creds)

    # Create a new ticket
    for ticket in tickets:
        print ticket
        ticket = Ticket(**ticket)
        zenpy_client.ticket_import.create(ticket)

    ## Perform a simple search
    #for ticket in zenpy_client.search("party", type='ticket', assignee="face"):
    #    print(ticket)

def generate_tickets(num):
    status = ['new','open','pending','hold','solved','closed']
    prios  = ['low', 'medium', 'high', 'urgent']
    types  = ['ticket', 'incident', 'task', 'problem', 'question']

    fake = Faker('en_US')
    #[{'subject':'test','priority':'medium','status':'open','summary':'Help me!','description':'Please help me!!','type':'problem','created_at':created,'updated_at':updated}]
    tickets = []
    for x in range(0, num):
        created_offset = randint(0,90)
        updated_offset = randint(0,created_offset)
        due_offset     = randint(-90,created_offset)

        created = datetime.datetime.now() - datetime.timedelta(days=created_offset)
        updated = datetime.datetime.now() - datetime.timedelta(days=updated_offset)
        due     = datetime.datetime.now() - datetime.timedelta(days=due_offset)
        if randint(0,1) == 1:
            due = None

        subject = fake.text()
        subject = subject[0:46]

        ticket = {
            'subject':      subject,
            'description':  fake.text(),
            'priority':     prios[ randint(0, len(prios)-1) ],
            'status':       status[ randint(0, len(status)-1) ],
            'type':         types[ randint(0, len(types)-1) ],
            'created_at':   created,
            'updated_at':   updated,
            'due_at':       due
        }

        tickets.append(ticket)

    return tickets

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


    tickets = generate_tickets(100)
    #print tickets
    import_tickets(tickets)
