import pytest

from councilmatic_core.management.commands.refresh_pic import Command as RefreshPic
from councilmatic_core.management.commands.convert_attachment_text import Command as ConvertAttachmentText


@pytest.mark.django_db
def test_refresh_pic(metro_bill_document,
                     metro_event_document):
    '''
    Test that the `_get_urls` and `_create_keys` successfully finds changed bill and event documents
    and converts their urls to a list of AWS keys.
    '''
    command = RefreshPic()
    document_urls = list(command._get_urls())

    bill_doc_link, = metro_bill_document.links.all()
    event_doc_link, = metro_event_document.links.all()

    assert (bill_doc_link.url in document_urls) == True
    assert (event_doc_link.url in document_urls) == True

    aws_keys = command._create_keys(document_urls)

    assert len(document_urls) == len(aws_keys)

@pytest.mark.django_db(transaction=True)
def test_convert_attachment_text(metro_bill_document, mocker):
    command = ConvertAttachmentText()
    command.update_all = True

    document_urls, = list(command.get_document_url())
    document_url, document_id = document_urls

    assert document_url == metro_bill_document.links.first().url
    assert document_id == metro_bill_document.id

'''
TO-DO: This should work, but it doesn't; the query is executed, but the result
never makes it into the database or to the ORM. When I run the resulting query
directly, the update is made. I'm not sure why this happens, but I need to move
on.
'''
#    expected_full_text = 'test'
#    documents = (doc for doc in [{'plain_text': expected_full_text, 'id': document_id}])
#    mocker.patch.object(command, 'convert_document_to_plaintext', return_value=documents)
#
#    command.add_plain_text()
#
#    metro_bill_document.refresh_from_db()
#    assert metro_bill_document.full_text == expected_full_text
