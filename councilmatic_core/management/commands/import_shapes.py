import json

import requests
from django.core.management.base import BaseCommand
from councilmatic_core import models


class Command(BaseCommand):
    help = "Import boundary shapefiles for Post entities"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.Session()

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-url',
            help='The base URL for the API to use to retrieve boundaries',
            default='https://ocd.datamade.us',
        )
        parser.add_argument(
            'boundary_set',
            help='One or more slugs of boundary sets to retrieve',
            nargs='*',
            default=['chicago-wards-2015'],
        )

    def handle(self, *args, **options):
        self.stdout.write('Populating boundaries...')
        boundaries_populated = 0
        for boundary in options['boundary_set']:
            bndry_set_url = options['base_url'] + '/boundaries/' + boundary

            page_res = self.get_response(bndry_set_url + '/?limit=0')
            page_json = json.loads(page_res.text)

            for bndry_json in page_json['objects']:
                shape_url = options['base_url'] + bndry_json['url'] + 'shape'
                shape_res = self.get_response(shape_url)
                if shape_res:
                    if 'ocd-division' in bndry_json['external_id']:
                        filters = {
                            'division_id': bndry_json['external_id']
                        }
                    else:
                        # The API doesn't appear to use an OCD id as external_id,
                        # so we have to filter on a fragment of the Division ID
                        # instead of the entire ID
                        filters = {
                            'division_id__endswith': bndry_json['external_id']
                        }
                    models.Post.objects.filter(**filters).update(
                        shape=json.loads(shape_res.text)
                    )
                    boundaries_populated += 1
        self.stdout.write(
            self.style.SUCCESS(
                'Populated {} boundaries'.format(str(boundaries_populated))
            )
        )

    def get_response(self, url, params=None, timeout=60, **kwargs):
        """
        The OCD API has intermittently thrown 502 and 504 errors, so only proceed
        when receiving an 'ok' status.
        """
        response = self.session.get(url, params=params, timeout=timeout, **kwargs)

        if response.ok:
            return response
        else:
            message = '{url} returned a bad response - {status}'.format(
                url=url,
                status=response.status_code
            )
            raise requests.exceptions.HTTPError('ERROR: {0}'.format(message))

