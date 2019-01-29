import pytest
from pytest_django.fixtures import db
from uuid import uuid4

from django.core.management import call_command
from django.db import connection

from councilmatic_core.models import Bill, BillDocument, Event, EventDocument

@pytest.fixture
@pytest.mark.django_db
def organizations(db):
    call_command('loaddata', 'tests/fixtures/organization.json')

@pytest.fixture
@pytest.mark.django_db
def bills(db):
    call_command('loaddata', 'tests/fixtures/bill.json')

@pytest.fixture
@pytest.mark.django_db
def people(db):
    call_command('loaddata', 'tests/fixtures/person.json')

@pytest.fixture
@pytest.mark.django_db
def events(db):
    call_command('loaddata', 'tests/fixtures/event.json')

@pytest.fixture
@pytest.mark.django_db
def metro_bill(db):
    bill_info = {
        'ocd_id': 'ocd-bill/8ad8fe5a-59a0-4e06-88bd-58d6d0e5ef1a',
        'description': 'CONSIDER: A. AUTHORIZING the CEO to execute Modification No. 2 to Contract C1153, Advanced Utility Relocations (Westwood/UCLA Station), with Steve Bubalo Construction Company for supply and installation of equipment for a traffic Video Detection System (VDS) required by Los Angeles Department of Transportation (LADOT), in the amount of $567,554, increasing the total contract value from $11,439,000 to $12,006,554; and B. APPROVING an increase in Contract Modification Authority (CMA) to Contract C1153, Advanced Utility Relocations (Westwood/UCLA Station), increasing the current CMA from $1,143,900 to $2,287,800.',
        'identifier': '2018-0285',
        'ocd_created_at': '2017-01-16 15:00:30.329048-06',
        'ocd_updated_at': '2017-01-16 15:00:30.329048-06',
        'updated_at': '2017-01-16 15:00:30.329048-06',
        }

    bill = Bill.objects.create(**bill_info)

    return bill

@pytest.fixture
@pytest.mark.django_db
def metro_event(db):
    event_info = {
        'ocd_id': 'ocd-event/17fdaaa3-0aba-4df0-9893-2c2e8e94d18d',
        'ocd_created_at': '2017-05-27 11:10:46.574-05',
        'ocd_updated_at': '2017-05-27 11:10:46.574-05',
        'name': 'System Safety, Security and Operations Committee',
        'start_time': '2017-05-18 12:15:00-05',
        'updated_at': '2017-05-17 11:06:47.1853',
        'slug': uuid4(),
    }

    event = Event.objects.create(**event_info)

    return event

@pytest.fixture
@pytest.mark.django_db
def metro_bill_document(metro_bill, db):
    document_info = {
        'bill_id': metro_bill.ocd_id,
        'document_type': 'V',
        'updated_at': '2017-02-16 15:00:30.329048-06',
        'full_text': '',
        'note': 'Board Report',
        'url': 'https://metro.legistar.com/ViewReport.ashx?M=R&N=TextL5&GID=557&ID=5016&GUID=LATEST&Title=Board+Report',
    }

    document = BillDocument.objects.create(**document_info)

    return document

@pytest.fixture
@pytest.mark.django_db
def metro_event_document(metro_event, db):
    document_info = {
        'event_id': metro_event.ocd_id,
        'updated_at': '2017-05-27 11:10:46.574-05',
        'full_text': '',
        'note': 'Agenda',
        'url': 'http://metro.legistar1.com/metro/meetings/2017/5/1216_A_System_Safety,_Security_and_Operations_Committee_17-05-18_Agenda.pdf',
    }

    document = EventDocument.objects.create(**document_info)

    return document

@pytest.fixture
@pytest.mark.django_db
def metro_change_bill(metro_bill, db):
    with connection.cursor() as cursor:
        sql = '''
            CREATE TABLE change_bill (
                ocd_id VARCHAR,
                PRIMARY KEY (ocd_id)
            );
            INSERT INTO change_bill (ocd_id)
            VALUES ('{}');
        '''.format(metro_bill.ocd_id)

        cursor.execute(sql)

@pytest.fixture
@pytest.mark.django_db
def metro_change_event(metro_event, db):
    with connection.cursor() as cursor:
        sql = '''
            CREATE TABLE change_event (
                ocd_id VARCHAR,
                PRIMARY KEY (ocd_id)
            );
            INSERT INTO change_event (ocd_id)
            VALUES ('{}');
        '''.format(metro_event.ocd_id)

        cursor.execute(sql)
