import datetime
import os
from uuid import uuid4

import pytest
from pytest_django.fixtures import db

from django.conf import settings
from django.db import connection

from councilmatic_core.models import Bill, Event
from opencivicdata.core.models import Jurisdiction, Division
from opencivicdata.legislative.models import (
    BillDocumentLink,
    EventDocument,
    EventDocumentLink,
    LegislativeSession,
    BillVersion,
    BillDocument,
    BillVersionLink,
)


@pytest.fixture
@pytest.mark.django_db
def jurisdiction(db):
    division = Division.objects.create(
        id=f"ocd-division/country:us/state:il/place:chicago-{str(uuid4())}",
        name="Chicago city",
    )

    return Jurisdiction.objects.create(
        **{
            "created_at": "2019-06-10T19:23:47.116Z",
            "updated_at": "2019-06-10T19:23:47.116Z",
            "name": "Chicago City Government",
            "url": "https://chicago.legistar.com/",
            "classification": "government",
            "division": division,
        }
    )


@pytest.fixture
@pytest.mark.django_db
def legislative_session(db, jurisdiction):
    session_info = {
        "id": str(uuid4()),
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
    file_directory = os.path.dirname(__file__)
    absolute_file_directory = os.path.abspath(file_directory)

    with open(
        os.path.join(absolute_file_directory, "fixtures", "bill_text.rtf"), "r"
    ) as f:
        bill_text = f.read()

    bill_info = {
        "id": "8ad8fe5a-59a0-4e06-88bd-58d6d0e5ef1a",
        "title": "CONSIDER: A. AUTHORIZING the CEO to execute Modification No. 2 to Contract C1153, Advanced Utility Relocations (Westwood/UCLA Station), with Steve Bubalo Construction Company for supply and installation of equipment for a traffic Video Detection System (VDS) required by Los Angeles Department of Transportation (LADOT), in the amount of $567,554, increasing the total contract value from $11,439,000 to $12,006,554; and B. APPROVING an increase in Contract Modification Authority (CMA) to Contract C1153, Advanced Utility Relocations (Westwood/UCLA Station), increasing the current CMA from $1,143,900 to $2,287,800.",
        "identifier": "2018-0285",
        "created_at": "2017-01-16 15:00:30.329048-06",
        "updated_at": datetime.datetime.now().isoformat(),
        "legislative_session": legislative_session,
        "extras": {"rtf_text": bill_text},
    }

    bill = Bill.objects.create(**bill_info)

    return bill


@pytest.fixture
@pytest.mark.django_db
def metro_event(db, jurisdiction):
    event_info = {
        "id": "ocd-event/17fdaaa3-0aba-4df0-9893-2c2e8e94d18d",
        "created_at": "2017-05-27 11:10:46.574-05",
        "updated_at": datetime.datetime.now().isoformat(),
        "name": "System Safety, Security and Operations Committee",
        "start_date": "2017-05-18 12:15:00-05",
        "jurisdiction": jurisdiction,
    }

    event = Event.objects.create(**event_info)

    return event


@pytest.fixture
@pytest.mark.django_db(transaction=True)
def ocd_bill_document(metro_bill, transactional_db):
    document_info = {
        "bill_id": metro_bill.id,
        "note": "Board Report",
    }

    document = BillDocument.objects.create(**document_info)

    document_link_info = {
        "url": "http://metro.legistar1.com/metro/attachments/e041786b-a42a-4d03-bd3e-06d5b3113de2.pdf",
        "document": document,
    }

    BillDocumentLink.objects.create(**document_link_info)

    version = BillVersion.objects.create(
        bill=metro_bill, note="test", date="1992-02-16"
    )

    BillVersionLink.objects.create(
        version=version,
        url="https://metro.legistar.com/ViewReport.ashx?M=R&N=TextL5&GID=557&ID=5016&GUID=LATEST&Title=Board+Report.pdf",
    )

    metro_bill.versions.add(version)
    metro_bill.save()

    return document


@pytest.fixture
@pytest.mark.django_db
def metro_event_document(metro_event, db):
    document_info = {
        "event_id": metro_event.id,
        "note": "Agenda",
    }

    document = EventDocument.objects.create(**document_info)

    document_link_info = {
        "url": "http://metro.legistar1.com/metro/meetings/2017/5/1216_A_System_Safety,_Security_and_Operations_Committee_17-05-18_Agenda.pdf",
        "document": document,
    }

    EventDocumentLink.objects.create(**document_link_info)

    return document
