#!/usr/bin/env python
import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":

    try:
        if sys.argv[1] == "keepdb":
            keep = True
    except IndexError:
        keep = False

    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.test_settings"
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, keepdb=keep)
    failures = test_runner.run_tests(["councilmatic_core.tests"])
    sys.exit(bool(failures))
