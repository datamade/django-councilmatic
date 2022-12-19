import itertools
import logging
import logging.config
import os
import requests
import tempfile
import tqdm

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Max, Q

from opencivicdata.legislative.models import BillDocumentLink, BillDocument


# Configure logging
logging.config.dictConfig(settings.LOGGING)
logging.getLogger("requests").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Converts bill attachments into plain text"

    def add_arguments(self, parser):
        parser.add_argument(
            "--update_all",
            default=False,
            action="store_true",
            help="Add or update plain text for all bill attachments.",
        )

    def handle(self, *args, **options):
        self.update_all = options["update_all"]
        self.add_plain_text()

    def get_document_url(self):
        """
        By default, convert text for recently updated files, or files that
        do not have attachment text. Otherwise, convert text for all files.
        """
        max_updated = BillDocument.objects.all().aggregate(
            max_updated_at=Max("bill__updated_at")
        )["max_updated_at"]

        is_file = (
            Q(url__iendswith="pdf")
            | Q(url__iendswith="docx")
            | Q(url__iendswith="docx")
        )
        is_null = Q(document__extras__full_text__isnull=True)
        after_max_update = Q(document__bill__updated_at__gte=max_updated)

        if max_updated is None or self.update_all:
            qs = BillDocumentLink.objects.filter(is_file)
        else:
            # Always try to convert null files, because files may have failed
            # in a reparable manner, e.g., Legistar server errors, during a
            # previous conversion.
            qs = BillDocumentLink.objects.filter(is_file & (after_max_update | is_null))

        for item in qs:
            yield item.url, item.document.id

    def convert_document_to_plaintext(self):
        # textract is a heavy dependency. In order to test this code without
        # installing it, import the library here.
        import textract

        for url, document_id in tqdm.tqdm(self.get_document_url()):
            try:
                response = requests.get(url)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                # Don't fail due to server errors, as these tend to resolve themselves.
                # https://requests.readthedocs.io/en/master/user/quickstart/#errors-and-exceptions
                msg = (
                    "Document URL {} raised a server error - ".format(url)
                    + "Could not get attachment text!"
                )
                logger.warning(msg)
                continue

            if response.status_code != 200:
                msg = (
                    "Document URL {} returns {}".format(url, response.status_code)
                    + " - Could not get attachment text!"
                )
                logger.warning(msg)
                continue

            extension = os.path.splitext(url)[1]

            with tempfile.NamedTemporaryFile(suffix=extension) as tfp:
                tfp.write(response.content)

                try:
                    plain_text = textract.process(tfp.name)
                except textract.exceptions.ShellError as e:
                    logger.warning(
                        "{} - Could not convert Councilmatic Document ID {}!".format(
                            e, document_id
                        )
                    )
                    continue
                except TypeError as e:
                    if "decode() argument 1 must be str, not None" in str(e):
                        msg = "{} - Could not convert ".format(
                            e
                        ) + "Councilmatic Document ID {}!".format(document_id)
                        logger.warning(msg)
                        continue
                    else:
                        raise
                except UnicodeDecodeError as e:
                    logger.warning(
                        "{} - Could not convert Councilmatic Document ID {}!".format(
                            e, document_id
                        )
                    )
                    continue

                logger.info(
                    "Councilmatic Document ID {} - conversion complete".format(
                        document_id
                    )
                )

            yield (plain_text.decode("utf-8"), document_id)

    def add_plain_text(self):
        """
        Metro has over 2,000 attachments that should be converted into plain
        text. When updating all documents with `--update_all`, this function
        ensures that the database updates only 20 documents per connection
        (mainly, to avoid unexpected memory consumption). It fetches up to 20
        elements from a generator object, runs the UPDATE query, and then
        fetches up to 20 more.
        """
        update_statement = """
            UPDATE opencivicdata_billdocument AS bill_docs
            SET extras = jsonb_set(extras, '{full_text}', to_jsonb(cast(%s as text)))
            WHERE bill_docs.id = %s
        """

        plaintexts = self.convert_document_to_plaintext()

        while True:
            logger.info("Updating documents with plain text...")
            plaintexts_fetched_from_generator = list(itertools.islice(plaintexts, 20))

            if not plaintexts_fetched_from_generator:
                break
            else:
                with connection.cursor() as cursor:
                    cursor.executemany(
                        update_statement, plaintexts_fetched_from_generator
                    )

        logger.info("SUCCESS")
