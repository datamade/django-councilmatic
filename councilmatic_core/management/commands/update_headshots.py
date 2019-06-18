from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from django.conf import settings

from opencivicdata.core.models import Person as OCDPerson

import requests

class Command(BaseCommand):
    help = 'Attach headshots to councilmembers'

    def handle(self, *args, **opetions):
        for person in OCDPerson.objects.exclude(image=''):
            councilmatic_person = person.councilmatic_person
            filename = councilmatic_person.slug + '.jpg'
            response = requests.get(person.image)

            self.stdout.write('Downloading {}'.format(person.image))

            with open('/tmp/' + filename, 'wb') as f:
                f.write(response.content)

            with open('/tmp/' + filename, 'rb') as f:
                django_file = File(f)
                councilmatic_person.headshot.save(filename, django_file)

        self.stdout.write('Collecting static')

        call_command('collectstatic', verbosity=0, interactive=False)
