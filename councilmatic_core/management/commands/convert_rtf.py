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

    def handle(self, *args, **options):

        self.connection = engine.connect()

        '''
        This command converts RTF from Legistar into valid HTML.
        The conversion employs "unoconv" - a CLI tool that imports and exports documents in LibreOffice. We run unoconv as a daemon process and kill it when the conversions finish.
        Three steps occur: (1) querying the database for bill full_text (i.e., the RTF from Legistar), 
        (2) iteration over the query results, conversion to html, and creation of an inserts string,
        (3) updating the full_text field with new html.
        '''
        listener = subprocess.Popen(['unoconv', '--listener'])
        try:
            self.add_html()
        finally:
            listener.kill()

    def get_rtf(self):
        with self.connection.begin() as trans:
            self.connection.execute("SET local timezone to '{}'".format(settings.TIME_ZONE)) 
            # Only apply this query to most recently updated (or created) bills.
            max_updated = Bill.objects.all().aggregate(Max('ocd_updated_at'))['ocd_updated_at__max']
            if max_updated is None:
                max_updated = datetime.datetime(1900, 1, 1)    

            query = '''
            SELECT ocd_id, full_text
            FROM councilmatic_core_bill
            WHERE updated_at >= '{}'
            AND full_text is not null
            '''.format(max_updated)

            query_results = self.connection.execute(query).fetchall()

            self.log_message('Found {} bills with rtf to convert...'.format(len(query_results)),
                             style='SUCCESS')

            return query_results

    def convert_rtf(self):
        rtf_results = self.get_rtf()

        self.log_message('Ready to convert RTF....')

        inserts = ''
        for bill_data in rtf_results:
            ocd_id = bill_data['ocd_id']
            rtf_string = bill_data['full_text']
            
            process = subprocess.run(['unoconv', '--stdin', '--stdout', '-f', 'html'], input=rtf_string.encode(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15)
            # The error output remains noisy...I tried a few configurations, including the below.
            # process = subprocess.Popen(['unoconv', '--stdin', '--stdout', '-f', 'html'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            # html, err = process.communicate(input=rtf_string.encode())

            html = process.stdout.decode('utf-8')
            inserts += "('" + ocd_id + "'" + ',' + "'" + html + "'),"

            print('.', end='')
            sys.stdout.flush()
        
        self.log_message('Conversions complete!')      
        return inserts[:-1] # Remove trailing comma

    def add_html(self):
        inserts = self.convert_rtf()

        with self.connection.begin() as trans:
            self.connection.execute("SET local timezone to '{}'".format(settings.TIME_ZONE))

            query = '''
                UPDATE councilmatic_core_bill as bills
                SET full_text = new_data.html
                from (values
                    {}
                ) as new_data(ocd_id, html)
                WHERE new_data.ocd_id = bills.ocd_id  
            '''.format(inserts)

            self.connection.execute(query)

        self.log_message('Bills have valid, viewable HTML!',
                         fancy=True,
                         center=True,
                         style='SUCCESS')
 
    def log_message(self,
                    message,
                    fancy=False,
                    style='HTTP_SUCCESS',
                    center=False):

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = '{0} {1}'.format(timestamp, message)

        if center:
            padding = (70 - len(message)) / 2
            message = '{0}{1}{0}'.format(' ' * int(padding), message)

        if fancy:
            message = '\n{0}\n  {1}  \n{0}'.format('-' * 70, message)

        style = getattr(self.style, style)
        self.stdout.write(style('{}\n'.format(message)))