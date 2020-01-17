import datetime
from uuid import uuid4

import pytest
from pytest_django.fixtures import db

from django.conf import settings
from django.db import connection

from councilmatic_core.models import Bill, Event
from opencivicdata.core.models import Jurisdiction, Division
from opencivicdata.legislative.models import BillDocumentLink, EventDocument, \
    EventDocumentLink, LegislativeSession, BillVersion, BillDocument


@pytest.fixture
@pytest.mark.django_db
def jurisdiction(db):
    division = Division.objects.create(
        id='ocd-division/country:us/state:il/place:chicago',
        name='Chicago city'
    )

    return Jurisdiction.objects.create(**{
        "created_at": "2019-06-10T19:23:47.116Z",
        "updated_at": "2019-06-10T19:23:47.116Z",
        "name": "Chicago City Government",
        "url": "https://chicago.legistar.com/",
        "classification": "government",
        "division": division
    })

@pytest.fixture
@pytest.mark.django_db
def legislative_session(db, jurisdiction):
    session_info = {
        "id": "ee9037fa-59bf-43c7-a2f1-7c853b3e71e2",
        "jurisdiction": jurisdiction,
        "identifier": "2011",
        "name": "2011 Regular Session",
        "classification": "",
        "start_date": "2011-05-18",
        "end_date": "2015-05-17",
    }

    session, _ = LegislativeSession.objects.get_or_create(**session_info)

    return session

@pytest.fixture
@pytest.mark.django_db
def metro_bill(db, legislative_session):
    bill_info = {
        'id': '8ad8fe5a-59a0-4e06-88bd-58d6d0e5ef1a',
        'title': 'CONSIDER: A. AUTHORIZING the CEO to execute Modification No. 2 to Contract C1153, Advanced Utility Relocations (Westwood/UCLA Station), with Steve Bubalo Construction Company for supply and installation of equipment for a traffic Video Detection System (VDS) required by Los Angeles Department of Transportation (LADOT), in the amount of $567,554, increasing the total contract value from $11,439,000 to $12,006,554; and B. APPROVING an increase in Contract Modification Authority (CMA) to Contract C1153, Advanced Utility Relocations (Westwood/UCLA Station), increasing the current CMA from $1,143,900 to $2,287,800.',
        'identifier': '2018-0285',
        'created_at': '2017-01-16 15:00:30.329048-06',
        'updated_at': datetime.datetime.now().isoformat(),
        'legislative_session': legislative_session,
    }

    bill = Bill.objects.create(**bill_info)

    return bill

@pytest.fixture
@pytest.mark.django_db
def metro_event(db, jurisdiction):
    event_info = {
        'id': 'ocd-event/17fdaaa3-0aba-4df0-9893-2c2e8e94d18d',
        'created_at': '2017-05-27 11:10:46.574-05',
        'updated_at': datetime.datetime.now().isoformat(),
        'name': 'System Safety, Security and Operations Committee',
        'start_date': '2017-05-18 12:15:00-05',
        'jurisdiction': jurisdiction,
    }

    event = Event.objects.create(**event_info)

    return event

@pytest.fixture
@pytest.mark.django_db(transaction=True)
def metro_bill_document(metro_bill, transactional_db):
    document_info = {
        'bill_id': metro_bill.id,
        'note': 'Board Report',
    }

    document = BillDocument.objects.create(**document_info)

    document_link_info = {
        'url': 'https://metro.legistar.com/ViewReport.ashx?M=R&N=TextL5&GID=557&ID=5016&GUID=LATEST&Title=Board+Report.pdf',
        'document': document,
    }

    BillDocumentLink.objects.create(**document_link_info)

    version = BillVersion.objects.create(bill=metro_bill,
                                         note='test',
                                         date='1992-02-16')

    metro_bill.versions.add(version)
    metro_bill.save()

    return document

@pytest.fixture
@pytest.mark.django_db
def metro_event_document(metro_event, db):
    document_info = {
        'event_id': metro_event.id,
        'note': 'Agenda',
    }

    document = EventDocument.objects.create(**document_info)

    document_link_info = {
        'url': 'http://metro.legistar1.com/metro/meetings/2017/5/1216_A_System_Safety,_Security_and_Operations_Committee_17-05-18_Agenda.pdf',
        'document': document,
    }

    EventDocumentLink.objects.create(**document_link_info)

    return document
