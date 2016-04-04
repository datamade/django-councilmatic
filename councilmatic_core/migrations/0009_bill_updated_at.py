# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('councilmatic_core', '0008_bill_ocr_full_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='updated_at',
            field=models.DateTimeField(default=datetime.datetime(
                2016, 1, 20, 18, 38, 27, 47441, tzinfo=utc), auto_now=True),
            preserve_default=False,
        ),
    ]
