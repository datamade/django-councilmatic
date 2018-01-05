import os
import sys
import subprocess
import logging
import logging.config
import sqlalchemy as sa

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Max

from councilmatic_core.models import Bill

DB_CONN = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'

engine = sa.create_engine(DB_CONN.format(**settings.DATABASES['default']),
                          convert_unicode=True,
                          server_side_cursors=True)

class Command(BaseCommand):
    help = 'Converts rtf-formatted legislative text to valid html'
    update_since = None


    def add_arguments(self, parser):
        parser.add_argument('--update_since',
                            help='Only update bills in the database that have changed since this date')


    def handle(self, *args, **options):

        self.connection = engine.connect()

        if options['update_since']:
            self.update_since = date_parser.parse(options['update_since'])

        listener = subprocess.Popen(['unoconv', '--listener'])
        try:
            self.convert_rtf()
        finally:
            listener.kill()


        # if options['update_since']:
        #     self.update_since = date_parser.parse(options['update_since'])

        # try:
        #     etl_method = getattr(self, '{}_etl'.format(endpoint))
        #     etl_method(import_only=import_only,
        #                download_only=download_only,
        #                delete=options['delete'])

        # except Exception as e:
        #     client.captureException()
        #     logger.error(e, exc_info=True)

    # This function logs a message about successful data imports - put this in a utils file. 
    def log_message(self,
                    message,
                    fancy=False,
                    style='HTTP_SUCCESS',
                    art_file=None,
                    center=False,
                    timestamp=True):

        if timestamp:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message = '{0} {1}'.format(now, message)

        if len(message) < 70 and center:
            padding = (70 - len(message)) / 2
            message = '{0}{1}{0}'.format(' ' * int(padding), message)

        if fancy and not art_file:
            thing_count = len(message) + 2

            message = '\n{0}\n  {1}  \n{0}'.format('-' * 70, message)

        elif art_file:
            art = open(os.path.join(self.this_folder, 'art', art_file)).read()
            message = '\n{0} \n {1}'.format(art, message)

        style = getattr(self.style, style)
        self.stdout.write(style('{}\n'.format(message)))


    def convert_rtf(self):
        # Query database for full_text
        with self.connection.begin() as trans:
            self.connection.execute("SET local timezone to '{}'".format(settings.TIME_ZONE)) 


            if self.update_since is None:
                max_updated = Bill.objects.all().aggregate(Max('ocd_updated_at'))['ocd_updated_at__max']

                if max_updated is None:
                    max_updated = datetime.datetime(1900, 1, 1)
            else:
                max_updated = self.update_since      

            query = '''
            SELECT ocd_id, full_text
            FROM councilmatic_core_bill
            WHERE updated_at >= '{}'
            LIMIT 5
            '''.format(max_updated)

            rtf_results = self.connection.execute(query).fetchall()

            # Make a list of dicts
            rtf_results_dict = [dict(bill_row) for bill_row in rtf_results]

        # Iterate over the resutls of previous query, convert the full_text to html, and push into an inserts list
        inserts = ''
        for bill_data in rtf_results:
            ocd_id = bill_data['ocd_id']
            rtf_string = bill_data['full_text']
            
            process = subprocess.run(['unoconv', '--stdin', '--stdout', '-f', 'html'], input=rtf_string.encode(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15)

            full_text = process.stdout.decode('utf-8')

            inserts += "('" + ocd_id + "'" + ',' + "'" + full_text + "'),"
            
        inserts = inserts[:-1] # Remove trailing comma

        # Update the full_text with new html
        query = '''
            UPDATE councilmatic_core_bill as bills
            SET full_text = new_data.html
            from (values
                {}
            ) as new_data(ocd_id, html)
            WHERE new_data.ocd_id = bills.ocd_id  
        '''.format(inserts)


        self.connection.execute(query)

        # self.log_message('Organizations Complete!',
        #                  fancy=True,
        #                  center=True,
        #                  style='SUCCESS')

