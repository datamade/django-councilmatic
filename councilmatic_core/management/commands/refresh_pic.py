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

from opencivicdata.legislative.models import BillDocumentLink, BillVersionLink, \
    EventDocumentLink, EventRelatedEntity


for configuration in ['AWS_KEY','AWS_SECRET']:
    if not hasattr(settings, configuration):
        raise ImproperlyConfigured(
            'Please define {0} in settings_deployment.py'.format(configuration))


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Refreshes the property image cache by deleting documents that need to be newly created'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.local_now = pytz.timezone(settings.TIME_ZONE)\
                             .localize(datetime.datetime.now())

        self.bills_on_upcoming_agendas = EventRelatedEntity.objects.filter(
            bill__isnull=False,
            agenda_item__event__start_date__gte=self.local_now
        ).values_list('bill__id')

    def handle(self, *args, **options):
        from boto.s3.connection import S3Connection
        from boto.s3.key import Key
        from boto.exception import S3ResponseError

        s3_conn = S3Connection(settings.AWS_KEY, settings.AWS_SECRET)

        document_urls = self._get_urls()
        aws_keys = self._create_keys(document_urls)
        bucket = s3_conn.get_bucket('councilmatic-document-cache')
        bucket.delete_keys(aws_keys)

        success_message = 'Removed {} document(s) from the councilmatic-document-cache'.format(len(aws_keys))
        logger.info(success_message)

    def _get_bill_versions(self, window_start):
        '''
        Retrieve URLs of updated and upcoming versions, i.e., the bills
        themselves.
        '''
        recently_updated = Q(version__bill__updated_at__gte=window_start)
        upcoming = Q(version__bill__id__in=self.bills_on_upcoming_agendas)

        return BillVersionLink.objects.filter(
            recently_updated | upcoming
        ).values_list('url', flat=True)

    def _get_bill_documents(self, window_start):
        '''
        Retrieve URLs of updated and upcoming documents, i.e., attachments
        to bills (versions).
        '''
        has_versions = Q(document__bill__versions__isnull=False)
        recently_updated = Q(document__bill__updated_at__gte=window_start)
        upcoming = Q(document__bill__id__in=self.bills_on_upcoming_agendas)

        return BillDocumentLink.objects.filter(
            has_versions & (recently_updated | upcoming)
        ).values_list('url', flat=True)

    def _get_event_documents(self, window_start):
        '''
        Retrieve URLs of updated and upcoming event documents, i.e., agendas.
        '''
        recently_updated = Q(document__event__updated_at__gte=window_start)
        upcoming = Q(document__event__start_date__gte=self.local_now)

        return EventDocumentLink.objects.filter(
            recently_updated | upcoming
        ).values_list('url', flat=True)

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
        one_hour_ago = self.local_now - datetime.timedelta(hours=1)

        return itertools.chain(
            self._get_bill_versions(one_hour_ago),
            self._get_bill_documents(one_hour_ago),
            self._get_event_documents(one_hour_ago)
        )

    def _create_keys(self, document_urls):
        return [urllib.parse.quote_plus(url) for url in document_urls]
