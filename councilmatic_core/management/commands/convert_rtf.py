import os
import sys
import subprocess
import logging
import logging.config
import sqlalchemy as sa
import datetime

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Max

from councilmatic_core.models import Bill

logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger(__name__)

DB_CONN = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'

engine = sa.create_engine(DB_CONN.format(**settings.DATABASES['default']),
                          convert_unicode=True,
                          server_side_cursors=True)

class Command(BaseCommand):
    help = 'Converts rtf-formatted legislative text to valid html'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update_all',
            default=False,
            help='Update full_text in all bills: can be set to True.')

    def handle(self, *args, **options):
        self.connection = engine.connect()
        self.update_all = options['update_all']
        '''
        This command converts RTF from Legistar into valid HTML.
        The conversion employs "unoconv" - a CLI tool that imports and exports documents in LibreOffice. We run unoconv as a daemon process and kill it when the conversions finish.
        Three steps occur: (1) querying the database for bill full_text (i.e., the RTF from Legistar), 
        (2) iteration over the query results, conversion to html, and creation of an inserts string,
        (3) updating the full_text field with new html.
        '''
        listener = subprocess.Popen(['unoconv', '--listener'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            self.add_html()
        finally:
            listener.kill()

    def get_rtf(self):
        self.connection.execute("SET local timezone to '{}'".format(settings.TIME_ZONE))
        with engine.begin() as connection:
            # Only apply this query to most recently updated (or created) bills.
            max_updated = Bill.objects.all().aggregate(Max('ocd_updated_at'))['ocd_updated_at__max']

            if max_updated is None or self.update_all:
                query = '''
                    SELECT ocd_id, full_text
                    FROM councilmatic_core_bill
                    WHERE full_text is not null
                    ORDER BY updated_at DESC
                '''    
            else:
                query = '''
                    SELECT ocd_id, full_text
                    FROM councilmatic_core_bill
                    WHERE updated_at >= :max_updated
                    AND full_text is not null
                    ORDER BY updated_at DESC
                '''

            result = connection.execution_options(stream_results=True).execute(sa.text(query), max_updated=max_updated)

            yield from result

    def convert_rtf(self):
        rtf_results = self.get_rtf()

        logger.info('Converting RTF to HTML....')

        inserts = ''
        for bill_data in rtf_results:
            ocd_id = bill_data['ocd_id']
            rtf_string = bill_data['full_text']
            
            try:
                process = subprocess.run(['unoconv', '--stdin', '--stdout', '-f', 'html'], input=rtf_string.encode(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15)
            except subprocess.TimeoutExpired as e:
                logger.error(e)
                continue

            html = process.stdout.decode('utf-8')

            logger.info('Successful conversion of {}'.format(ocd_id))

            yield {'html': html, 'ocd_id': ocd_id}
           

    def add_html(self):
        html_results = self.convert_rtf()

        self.connection.execute("SET local timezone to '{}'".format(settings.TIME_ZONE))
        query = '''
            UPDATE councilmatic_core_bill as bills
            SET html_text = :html
            WHERE bills.ocd_id = :ocd_id  
        '''

        chunk = []
        # for html, ocd_id in html_results:
        for bill_dict in html_results:
            chunk.append(bill_dict)
            if len(chunk) == 20:
                with self.connection.begin() as trans:
                    self.connection.execute(sa.text(query), chunk)
                    
                    chunk = []

        # Update bills when less than 1,000 elements in a chunk. 
        if chunk:
            with self.connection.begin() as trans:
                self.connection.execute(sa.text(query), chunk)

        logger.info('Bills have valid, viewable HTML!')
