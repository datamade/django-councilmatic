import pytest

from django.db import connection

from councilmatic_core.management.commands.refresh_pic import Command

@pytest.mark.django_db
def test_command_functions(metro_bill_document, 
                           metro_event_document):
    '''
    Test that the `_get_urls` and `_create_keys` successfully finds changed bill and event documents 
    and converts their urls to a list of AWS keys.
    '''
    refresh_pic_command = Command()
    document_urls = refresh_pic_command._get_urls()

    bill_doc_link, = metro_bill_document.links.all()
    event_doc_link, = metro_event_document.links.all()

    assert (bill_doc_link.url in document_urls) == True 
    assert (event_doc_link.url in document_urls) == True

    aws_keys = refresh_pic_command._create_keys(document_urls)

    assert len(document_urls) == len(aws_keys)





    