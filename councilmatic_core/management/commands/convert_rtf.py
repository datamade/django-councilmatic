import os
import sys
import subprocess
import logging
import logging.config
import sqlalchemy as sa
import datetime
import signal
import json

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Max, Q

from councilmatic_core.models import Bill

logging.config.dictConfig(settings.LOGGING)
logging.getLogger("requests").setLevel(logging.WARNING)
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
            action='store_true',
            help='Update html_text in all bills.')

        parser.add_argument(
            '--update_empty',
            default=False,
            action='store_true',
            help='Update bills that currently do not have html_text.')

    def handle(self, *args, **options):
        self.connection = engine.connect()
        self.update_all = options['update_all']
        self.update_empty = options['update_empty']
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
            listener.terminate()

    def get_rtf(self):
        self.connection.execute("SET local timezone to '{}'".format(settings.TIME_ZONE))
        '''
        The script, by default, only converts the most recently updated bills:
        the `max_updated` timestamp and the third (last) query option
        helps accomplish this.

        Specifically, the query determines which bills have been
        recently updated (or created) in the Councilmatic database,
        by looking for bills with an `updated_at` (i.e.,  max_updated)
        timestamp of equal or greater value.
        '''
        max_updated = Bill.objects.all().aggregate(Max('updated_at'))['updated_at__max']

        has_rtf_text = Q(extras__rtf_text__isnull=False)
        missing_html_text = Q(extras__html_text__isnull=True)
        after_max_update = Q(updated_at__gt=max_updated)

        if max_updated is None or self.update_all:
            qs = Bill.objects.filter(has_rtf_text)
        elif self.update_empty:
            qs = Bill.objects.filter(has_rtf_text & missing_html_text)
        else:
            qs = Bill.objects.filter(has_rtf_text & after_max_update)

        yield from qs

    def convert_rtf(self):
        rtf_results = self.get_rtf()

        logger.info('Converting RTF to HTML....')

        inserts = ''
        for bill in rtf_results:
            ocd_id = bill.id
            rtf_string = bill.extras['rtf_text']

            try:
                # For Python 3.4 and below
                process = subprocess.Popen(['unoconv', '--stdin', '--stdout', '-f', 'html'], preexec_fn=os.setsid, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

                html_data, stderr_data = process.communicate(input=rtf_string.encode(), timeout=15)

                html = html_data.decode('utf-8')
            except subprocess.TimeoutExpired as e:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)

                logger.error(e)
                logger.error('Look at bill {}'.format(ocd_id))
                continue

            logger.info('Successful conversion of {}'.format(ocd_id))

            yield {'html': json.dumps(html), 'ocd_id': ocd_id}

    def add_html(self):
        html_results = self.convert_rtf()

        self.connection.execute("SET local timezone to '{}'".format(settings.TIME_ZONE))
        query = '''
            UPDATE opencivicdata_bill
            SET extras = jsonb_set(extras, '{html_text}', :html)
            WHERE id = :ocd_id
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
