import os
import sys
import subprocess
import logging
import logging.config
import datetime
import signal
import json

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from django.db.models import Max, Q

import psycopg2
from psycopg2.extras import execute_batch

from councilmatic_core.models import Bill

logging.config.dictConfig(settings.LOGGING)
logging.getLogger("requests").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Converts RTF-formatted legislative text to valid HTML'

    def add_arguments(self, parser):
        parser.add_argument(
            "--update_all",
            default=False,
            action="store_true",
            help="Update html_text in all bills.",
        )

        parser.add_argument(
            "--update_empty",
            default=False,
            action="store_true",
            help="Update bills that currently do not have html_text.",
        )

    def handle(self, *args, **options):
        django_conn = connection.get_connection_params()

        conn_kwargs = {
            'user': django_conn.get('user', ''),
            'password': django_conn.get('password', ''),
            'host': django_conn.get('host', ''),
            'port': django_conn.get('port', ''),
            'dbname': django_conn.get('database', ''),
        }

        self.connection = psycopg2.connect(**conn_kwargs)
        self.update_all = options['update_all']
        self.update_empty = options['update_empty']

        listener = subprocess.Popen(['unoconv', '--listener'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        try:
            self.add_html()
        finally:
            listener.terminate()

    def get_rtf(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SET local timezone to '{}'".format(settings.TIME_ZONE))

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

        yield from qs.iterator()

    def get_html(self):
        logger.info('Converting RTF to HTML....')

        for bill in self.get_rtf():
            ocd_id = bill.id
            rtf_string = bill.extras["rtf_text"]

            try:
                process = subprocess.Popen(
                    ['unoconv', '--stdin', '--stdout', '-f', 'html'],
                    preexec_fn=os.setsid,
                    stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                )
                html_data, stderr_data = process.communicate(
                    input=rtf_string.encode(),  # TODO: Empty???
                    timeout=15
                )
                html = html_data.decode('utf-8')

            except subprocess.TimeoutExpired as e:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)

                logger.error(e)
                logger.error("Look at bill {}".format(ocd_id))

                continue

            print(rtf_string, html_data, html, ocd_id)

            logger.info("Successful conversion of {}".format(ocd_id))

            yield (json.dumps(html), ocd_id)

    def add_html(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SET local timezone to '{}'".format(settings.TIME_ZONE))

        query = '''
            UPDATE opencivicdata_bill
            SET extras = jsonb_set(extras, '{html_text}', %s)
            WHERE id = %s
        '''

        with self.connection.cursor() as cursor:
            execute_batch(cursor, query, self.get_html(), page_size=25)

        logger.info("Bills have valid, viewable HTML!")
