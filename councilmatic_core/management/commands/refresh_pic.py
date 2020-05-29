import datetime
import itertools
import logging
import logging.config
import urllib.parse

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q
import pytz

from opencivicdata.legislative.models import BillDocumentLink, EventDocumentLink


for configuration in ['AWS_KEY','AWS_SECRET']:
    if not hasattr(settings, configuration):
        raise ImproperlyConfigured(
            'Please define {0} in settings_deployment.py'.format(configuration))

logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Refreshes the property image cache by deleting documents that need to be newly created'

    def handle(self, *args, **options):
        from boto.s3.connection import S3Connection
        from boto.s3.key import Key
        from boto.exception import S3ResponseError

        document_urls = self._get_urls()
        aws_keys = self._create_keys(document_urls)

        s3_conn = S3Connection(settings.AWS_KEY, settings.AWS_SECRET)

        bucket = s3_conn.get_bucket('councilmatic-document-cache')

        bucket.delete_keys(aws_keys)

        logger.info(("Removed {} document(s) from the councilmatic-document-cache").format(len(aws_keys)))

    def _get_urls(self):
        '''
        Get the URLs of bill and event documents if the related bill or event
        has been updated in the past hour, or if they are releated to an event
        that is scheduled for a future date, as these are the documents that are
        most likely to change.

        This is a workaround for a known issue where making changes to data in
        Legistar (DataMade's source data system) does not always update timestamps
        that tell us to rescrape entities, toggling the updated timestamps in
        our database.
        '''
        app_timezone = pytz.timezone(settings.TIME_ZONE)
        one_hour_ago = app_timezone.localize(datetime.datetime.now()) - datetime.timedelta(hours=1)

        has_versions = Q(document__bill__versions__isnull=False)

        recently_updated = Q(document__bill__updated_at__gte=one_hour_ago)

        bills_on_upcoming_agendas = EventRelatedEntity.objects.filter(
            bill__isnull=False,
            agenda_item__event__start_date__gt=one_hour_ago
        ).values_list('bill__id')

        upcoming = Q(document__bill__id__in=bills_on_upcoming_agendas)

        bill_docs = BillDocumentLink.objects.filter(
            has_versions & (recently_updated | upcoming)
        ).values_list('url', flat=True)

        event_docs = EventDocumentLink.objects.filter(
            Q(document__event__updated_at__gte=one_hour_ago) | Q(document__event__start_date__gt=one_hour_ago)
        ).values_list('url', flat=True)

        return itertools.chain(bill_docs, event_docs)

    def _create_keys(self, document_urls):
        return [urllib.parse.quote_plus(url) for url in document_urls]
