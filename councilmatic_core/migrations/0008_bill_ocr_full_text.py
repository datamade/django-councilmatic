# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('councilmatic_core', '0007_auto_20151223_1150'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='ocr_full_text',
            field=models.TextField(blank=True),
        ),
    ]
