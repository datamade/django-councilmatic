import os
import logging
import logging.config
import sqlalchemy as sa
import requests
import textract
import tempfile
import itertools

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Max

from councilmatic_core.models import BillDocument

logging.config.dictConfig(settings.LOGGING)
logging.getLogger("requests").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

DB_CONN = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'

engine = sa.create_engine(DB_CONN.format(**settings.DATABASES['default']),
                          convert_unicode=True,
                          server_side_cursors=True)

class Command(BaseCommand):
    help = 'Converts bill attachments into plain text'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--update_all',
            default=False,
            action='store_true',
            help='Add or update plain text for all bill attachments.')

    def handle(self, *args, **options):
        self.update_all = options['update_all']
        self.add_plain_text()

    def get_document_url(self):
        with engine.begin() as connection:
            # Only apply this query to most recently updated (or created) bill documents.
            max_updated = BillDocument.objects.all().aggregate(Max('updated_at'))['updated_at__max']

            if max_updated is None or self.update_all:
                query = '''
                    SELECT id, url
                    FROM councilmatic_core_billdocument 
                    WHERE document_type='A' 
                    AND full_text is null
                    AND lower(url) similar to '%(.doc|.docx|.pdf)'
                    ORDER BY updated_at DESC
                ''' 
            else:
                query = '''
                    SELECT id, url
                    FROM councilmatic_core_billdocument 
                    WHERE updated_at >= :max_updated
                    AND document_type='A' 
                    AND full_text is null
                    AND lower(url) similar to '%(.doc|.docx|.pdf)'
                    ORDER BY updated_at DESC
                '''

            result = connection.execution_options(stream_results=True).execute(sa.text(query), max_updated=max_updated)

            yield from result

    def convert_document_to_plaintext(self):
        for document_data in self.get_document_url():
            document_data = dict(document_data)
            url = document_data['url']
            document_id = document_data['id']
            response = requests.get(url)
            # Sometimes, Metro Legistar has a URL that retuns a bad status code (e.g., 404 from http://metro.legistar1.com/metro/attachments/95d5007e-720b-4cdd-9494-c800392b9265.pdf). 
            # Skip these documents.
            if response.status_code != 200:
                logger.error('Document URL {} returns {} - Could not get attachment text!'.format(url, response.status_code))
                continue

            extension = os.path.splitext(url)[1]

            with tempfile.NamedTemporaryFile(suffix=extension) as tfp:
                tfp.write(response.content)

                try:
                    plain_text = textract.process(tfp.name)
                except textract.exceptions.ShellError as e:
                    logger.error('{} - Could not convert Document ID {}!'.format(e, document_id))
                    continue

                logger.info('Document ID {} - conversion complete'.format(document_id))

            yield {'plain_text': plain_text.decode('utf-8'), 'id': document_id}
            

    def add_plain_text(self):
        '''
        Metro has over 2,000 attachments that should be converted into plain text. 
        When updating all documents with `--update_all`, this function insures that the database updates only 20 documents per connection (mainly, to avoid unexpected memory consumption).
        It fetches up to 20 elements from a generator object, runs the UPDATE query, and then fetches up to 20 more.

        Inspired by: https://stackoverflow.com/questions/30510593/how-can-i-use-server-side-cursors-with-django-and-psycopg2/41088159#41088159

        More often, this script updates just a handful of documents: so, the incremental, fetch-just-20 approach may prove unnecessary. Possible refactor?
        '''

        update_statement = '''
            UPDATE councilmatic_core_billdocument as bill_docs
            SET full_text = :plain_text
            WHERE bill_docs.id = :id  
        '''
        
        plaintexts = self.convert_document_to_plaintext()

        while True:
            logger.info('Updating documents with plain text...')
            plaintexts_fetched_from_generator = list(itertools.islice(plaintexts, 20))

            if not plaintexts_fetched_from_generator:
                break
            else:
                with engine.begin() as connection:
                    connection.execute(sa.text(update_statement), plaintexts_fetched_from_generator)

        logger.info('SUCCESS')
