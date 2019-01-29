import pytest

from django.db import connection

from councilmatic_core.models import BillDocument
from councilmatic_core.management.commands.refresh_pic import Command

@pytest.mark.django_db
def test_command_functions(metro_bill_document, 
                           metro_change_bill,
                           metro_event_document,
                           metro_change_event):
    '''
    Test that the `_get_urls` and `_create_keys` successfully finds changed bill and event documents 
    and converts their urls to a list of AWS keys.
    '''
    refresh_pic_command = Command()
    document_urls = refresh_pic_command._get_urls()

    assert (metro_bill_document.url in document_urls) == True 
    assert (metro_event_document.url in document_urls) == True

    aws_keys = refresh_pic_command._create_keys(document_urls)

    assert len(document_urls) == len(aws_keys)





    