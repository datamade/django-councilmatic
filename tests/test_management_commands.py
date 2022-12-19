import os

from django.core.management import call_command
import pytest

from councilmatic_core.management.commands.refresh_pic import Command as RefreshPic
from councilmatic_core.management.commands.convert_attachment_text import (
    Command as ConvertAttachmentText,
)


@pytest.mark.django_db
def test_refresh_pic(ocd_bill_document, metro_event_document):
    """
    Test that the `_get_urls` and `_create_keys` successfully finds changed
    bill and event documents and converts their urls to a list of AWS keys.
    """
    command = RefreshPic()
    document_urls = list(command._get_urls())

    # Test that each of the URLs we expect exist, and that no other URLs
    # exist.
    (bill_version_link,) = ocd_bill_document.bill.versions.get().links.all()
    (bill_doc_link,) = ocd_bill_document.links.all()
    (event_doc_link,) = metro_event_document.links.all()

    assert len(document_urls) == 3

    assert bill_version_link.url in document_urls
    assert bill_doc_link.url in document_urls
    assert event_doc_link.url in document_urls

    # Test that creating keys from URLs yields the correct number of keys.
    aws_keys = command._create_keys(document_urls)

    assert len(document_urls) == len(aws_keys)


@pytest.mark.django_db(transaction=True)
def test_convert_attachment_text(ocd_bill_document, mocker):
    command = ConvertAttachmentText()
    command.update_all = True

    (document_urls,) = list(command.get_document_url())
    document_url, document_id = document_urls

    assert document_url == ocd_bill_document.links.first().url
    assert document_id == ocd_bill_document.id

    expected_full_text = "test"
    documents = (doc for doc in [(expected_full_text, document_id)])
    mocker.patch.object(
        command, "convert_document_to_plaintext", return_value=documents
    )

    command.add_plain_text()

    ocd_bill_document.refresh_from_db()


@pytest.mark.xfail
@pytest.mark.django_db
def test_convert_rtf(metro_bill):
    call_command("convert_rtf", "--update_all")

    metro_bill.refresh_from_db()

    file_directory = os.path.dirname(__file__)
    absolute_file_directory = os.path.abspath(file_directory)

    with open(
        os.path.join(absolute_file_directory, "fixtures", "bill_text.html"), "r"
    ) as f:
        expected_html = f.read()

    assert metro_bill.extras["html_text"] == expected_html
