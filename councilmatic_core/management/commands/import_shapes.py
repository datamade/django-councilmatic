import json

from django.core.management.base import BaseCommand
from councilmatic_core import models


class Command(BaseCommand):
    help = "Import boundary shapefiles for Post entities"

    def add_arguments(self, parser):
        parser.add_argument(
            'shape_file',
            help=(
                'The location of the file containing shapes for each Division, '
                'relative to the project root. The file should be formatted as JSON '
                'with each key corresponding to a Division ID and each value corresponding'
                'to a GeoJSON Feature object.'
            )
        )

    def handle(self, *args, **options):
        self.stdout.write('Populating shapes for Posts...')
        shapes_populated = 0

        with open(options['shape_file']) as shapef:
            shapes = json.load(shapef)

        for division_id, shape in shapes.items():
            models.Post.objects.filter(division_id=division_id).update(
                shape=shape
            )
            shapes_populated += 1

        self.stdout.write(
            self.style.SUCCESS(
                'Populated {} shapes'.format(str(shapes_populated))
            )
        )
