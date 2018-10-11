import pytest
from pytest_django.fixtures import db

from django.core.management import call_command


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