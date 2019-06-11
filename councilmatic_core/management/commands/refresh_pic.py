import urllib.parse
import logging
import logging.config

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings

for configuration in ['AWS_KEY','AWS_SECRET']:
    if not hasattr(settings, configuration):
        raise ImproperlyConfigured(
            'Please define {0} in settings_deployment.py'.format(configuration))

logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Refreshes the property image cache by deleting documents that need to be newly created'

    def handle(self, *args, **options):
        from boto.s3.connection import S3Connection
        from boto.s3.key import Key
        from boto.exception import S3ResponseError

        document_urls = self._get_urls()
        aws_keys = self._create_keys(document_urls)

        s3_conn = S3Connection(settings.AWS_KEY, settings.AWS_SECRET)

        bucket = s3_conn.get_bucket('councilmatic-document-cache')

        bucket.delete_keys(aws_keys)
    
        logger.info(("Removed {} document(s) from the councilmatic-document-cache").format(len(aws_keys)))

    def _get_urls(self):
        '''
        Three select statements:
        
        (1) change_bill
        Why? The ocr_full_text of a bill presents the same text as on the document. 
        When a bill's ocr_full_text changes, `import_data` adds that bill to the `change_bill` table. 
        We can query the `change_bill` table to determine which bill documents (potentially) changed, too. 

        (2) councilmatic_core_eventagendaitem
        Why? The event agenda items contain the text of the agenda.
        `import_data` does not have a "change" table for event agenda items 
        (otherwise, the database ends up with an overabundance of items: https://github.com/datamade/django-councilmatic/pull/140)
        If an agenda item has been updated, i.e., newly created, then assume that the event document changed, too.

        (3) change_event
        Why? The date, name, or other details of the event may have changed, and the document would have been updated in turn.

        '''
        with connection.cursor() as cursor:

            query = '''
                SELECT DISTINCT b_doc_link.url
                FROM opencivicdata_billversionlink AS b_version_link
                JOIN opencivicdata_billversion AS b_version
                ON b_version_link.document_id = b_version.id
                JOIN opencivicdata_bill AS b 
                ON b.id = b_version.bill_id
                WHERE b.updated_at >= (NOW() - INTERVAL '1 hour')
                UNION
                SELECT DISTINCT e_doc_link.url
                FROM opencivicdata_eventdocumentlink AS e_doc_link
                JOIN opencivicdata_eventdocument as e_doc 
                ON e_doc_link.document_id = e_doc.id
                JOIN opencivicdata_event AS e
                ON e.id = e_doc.event_id
                WHERE e.updated_at >= (NOW() - INTERVAL '1 hour')
            '''

            cursor.execute(query)

            return [entry[0] for entry in cursor.fetchall()]

    def _create_keys(self, document_urls):
        return [urllib.parse.quote_plus(url) for url in document_urls]
