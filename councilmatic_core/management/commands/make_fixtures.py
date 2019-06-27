import os

import django
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Refresh the test fixtures from an instance database'

    def _id_gen(self, table):
        with connection.cursor() as cursor:
            cursor.execute('SELECT id FROM opencivicdata_{} LIMIT 3'.format(table))
            ids = [row[0] for row in cursor]
        return ids

    def handle(self, *args, **options):
        current_directory = os.path.dirname(__file__)

        outfiles = []

        for table in ('bill', 'person', 'organization', 'event'):
            args = ['dump_object', 'councilmatic_core.{}'.format(table.title())] + self._id_gen(table) + ['--kitchensink']
            outfile = os.path.join(current_directory, '..', '..', '..', '{}.json'.format(table))
            self.stdout.write('writing {}'.format(outfile))
            with open(outfile, 'w') as f:
                call_command(*args, stdout=f)
            outfiles.append(outfile)

        self.stdout.write('merging outfiles')
        
        with open(os.path.join(current_directory, '..', '..', '..', 'tests', 'fixtures', 'test_data.json'), 'w') as f:
            call_command('merge_fixtures', *outfiles, stdout=f)

        for f in outfiles:
            self.stdout.write('removing {}'.format(f))
            os.remove(f)
