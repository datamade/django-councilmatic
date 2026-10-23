import os
import subprocess
import logging
import logging.config
import signal

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Max, Q

from councilmatic_core.models import Bill

logging.config.dictConfig(settings.LOGGING)
logging.getLogger("requests").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Converts RTF-formatted legislative text to valid HTML"

    def add_arguments(self, parser):
        parser.add_argument(
            "--update_all",
            default=False,
            action="store_true",
            help="Update html_text in all bills.",
        )

        parser.add_argument(
            "--update_empty",
            default=False,
            action="store_true",
            help="Update bills that currently do not have html_text.",
        )

    def handle(self, *args, **options):
        self.update_all = options["update_all"]
        self.update_empty = options["update_empty"]

        listener = subprocess.Popen(
            ["unoconv", "--listener"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        try:
            self.add_html()
        finally:
            listener.terminate()

    def get_rtf(self):
        max_updated = Bill.objects.all().aggregate(Max("updated_at"))["updated_at__max"]

        has_rtf_text = Q(extras__rtf_text__isnull=False)
        missing_html_text = Q(extras__html_text__isnull=True)
        after_max_update = Q(updated_at__gt=max_updated)

        if max_updated is None or self.update_all:
            qs = Bill.objects.filter(has_rtf_text)
        elif self.update_empty:
            qs = Bill.objects.filter(has_rtf_text & missing_html_text)
        else:
            qs = Bill.objects.filter(has_rtf_text & after_max_update)

        yield from qs.iterator()

    def get_html(self):
        logger.info("Converting RTF to HTML....")

        for bill in self.get_rtf():
            ocd_id = bill.id
            rtf_string = bill.extras["rtf_text"]

            process = subprocess.Popen(
                ["unoconv", "--stdin", "--stdout", "-f", "html"],
                preexec_fn=os.setsid,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            try:
                stdout_data, _ = process.communicate(
                    input=rtf_string.encode(), timeout=30
                )

            except subprocess.TimeoutExpired as e:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)

                logger.error(e)
                logger.error("Look at bill {}".format(ocd_id))
                continue

            else:
                html = stdout_data.decode("utf-8")

            try:
                assert html

            except AssertionError:
                logger.error(f"Converted HTML for bill {ocd_id} is empty")
                continue

            logger.info("Successful conversion of {}".format(ocd_id))

            bill.extras["html_text"] = html

            yield bill

    def add_html(self):
        Bill.objects.bulk_update(self.get_html(), ["extras"], batch_size=100)

        logger.info("Bills have valid, viewable HTML!")
