import os
import sys
import subprocess
import logging
import logging.config
import sqlalchemy as sa
import datetime
import signal
import os

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

    def handle(self, *args, **options):
        self.connection = engine.connect()

        self.add_plain_text()
        
        # listener = subprocess.Popen(['unoconv', '--listener'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # try:
        #     self.add_html()
        # finally:
        #     listener.terminate()

    def get_document_url(self):
        self.connection.execute("SET local timezone to '{}'".format(settings.TIME_ZONE))
        with engine.begin() as connection:
            # Only apply this query to most recently updated (or created) bills.
            # max_updated = BillDocument.objects.all().aggregate(Max('ocd_updated_at'))['ocd_updated_at__max']

            query = '''
                SELECT id, url
                FROM councilmatic_core_billdocument 
                WHERE document_type='A' 
                AND full_text is null
                ORDER BY updated_at DESC
            '''
            result = connection.execution_options(stream_results=True).execute(sa.text(query))

            yield from result

    def convert_document(self):
        documents = self.get_document_url()

        logger.info('Converting document to plain text...')

        for document_data in documents:
            document_data = dict(document_data)
            url = document_data['url']
            document_id = document_data['id']
           
            if url.endswith('doc') or url.endswith('docx'):
                try:
                    # For Python 3.4 and below
                    process = subprocess.Popen(['unoconv', '--stdout', '-f', 'text', url], preexec_fn=os.setsid, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

                    plain_text, stderr_data = process.communicate(timeout=15)

                except subprocess.TimeoutExpired as e:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    logger.error(e)
                    continue

                logger.info('Successful conversion of {}'.format(url))

                yield {'plain_text': plain_text.decode('utf-8'), 'id': document_id}

    def add_plain_text(self):
        plain_text_results = self.convert_document()

        print(plain_text_results, "$$$")

        self.connection.execute("SET local timezone to '{}'".format(settings.TIME_ZONE))
        query = '''
            UPDATE councilmatic_core_billdocument as bill_docs
            SET full_text = :full_text
            WHERE bill_docs.id = :id  
        '''

        chunk = []

        for doc_dict in plain_text_results:
            chunk.append(doc_dict)
            if len(chunk) == 20:
                with self.connection.begin() as trans:
                    self.connection.execute(sa.text(query), chunk)
                    
                    chunk = []

        # Update bills when less than 1,000 elements in a chunk. 
        if chunk:
            with self.connection.begin() as trans:
                self.connection.execute(sa.text(query), chunk)

        logger.info('SUCCESS')
