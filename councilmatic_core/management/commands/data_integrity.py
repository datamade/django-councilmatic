import pysolr
import requests
import logging
import logging.config

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from councilmatic_core.models import Bill


logging.config.dictConfig(settings.LOGGING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("pysolr").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Checks for alignment between the Solr index and Councilmatic database'

    def handle(self, *args, **options):
        
        councilmatic_count = self.count_councilmatic_bills()

        try:
            solr_url = settings.HAYSTACK_CONNECTIONS['default']['URL']
            requests.get(solr_url)
        except requests.ConnectionError:
            message = "ConnectionError: Unable to connect to Solr at {} when running the data integrity check. Is Solr running?".format(solr_url)
            logger.error(message)
            raise Exception(message)

        solr = pysolr.Solr(solr_url)
        solr_index_count = solr.search(q='*:*').hits

        if solr_index_count != councilmatic_count:
            message = 'Solr index has {solr} entites. The Councilmatic database has {councilmatic} entities. That\'s a problem!'.format(solr=solr_index_count, councilmatic=councilmatic_count)
            logger.error(message)
            print('. . . . .\n')

            raise AssertionError(message)

        logger.info('Good news! Solr index has {solr} entites. The Councilmatic database has {councilmatic} entities.'.format(solr=solr_index_count, councilmatic=councilmatic_count))
        print('. . . . .\n')

    def count_councilmatic_bills(self):

        return Bill.objects.all().count()