from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.exception import S3ResponseError

import urllib.parse

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings

for configuration in ['AWS_KEY','AWS_SECRET']:
    if not hasattr(settings, configuration):
        raise ImproperlyConfigured(
            'Please define {0} in settings_deployment.py'.format(configuration))


class Command(BaseCommand):
    help = 'Refreshes the property image cache by deleting documents that need to be newly created'

    def handle(self, *args, **options):
        document_urls = self._get_urls()
        aws_keys = self._create_keys(document_urls)

        s3_conn = S3Connection(settings.AWS_KEY, settings.AWS_SECRET)
        bucket = s3_conn.get_bucket('councilmatic-document-cache')

        bucket.delete_keys(aws_keys)
    
        print(("Removed {} document(s) from the councilmatic-document-cache").format(len(aws_keys)))

    def _get_urls(self):
        '''
        Select URLs from two tables:
        
        (1) councilmatic_core_billdocument
        Why? The ocr_full_text of a bill presents the its text, i.e., the text on the PDF. 
        When a bill's ocr_full_text changes, `import_data` adds that bill to the `change_bill` table. 
        We can query the `change_bill` table to determine which bill documents (potentially) changed, too. 

        (2) councilmatic_core_eventdocument
        Why? The event agenda items contain the text of the agenda.
        `import_data` does not have a "change" table for event agenda items 
        (otherwise, the database ends up with an overabundance of items: https://github.com/datamade/django-councilmatic/pull/140)
        If an agenda item has been updated, i.e., newly created, then assume that the event document changed, too.
        '''
        with connection.cursor() as cursor:

            query = '''
                SELECT DISTINCT url from 
                councilmatic_core_billdocument as b_doc
                JOIN change_bill 
                ON change_bill.ocd_id=b_doc.bill_id
                WHERE document_type='V'
                UNION
                SELECT DISTINCT url from 
                councilmatic_core_eventdocument as e_doc 
                INNER JOIN councilmatic_core_eventagendaitem as e_item
                ON e_doc.event_id=e_item.event_id
                WHERE e_item.updated_at >= (NOW() - INTERVAL '1 hour')
            '''

            cursor.execute(query)

            return [entry[0] for entry in cursor.fetchall()]

    def _create_keys(self, document_urls):
        return [urllib.parse.quote_plus(url) for url in document_urls]
