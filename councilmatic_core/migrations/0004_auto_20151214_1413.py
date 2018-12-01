# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('councilmatic_core', '0003_auto_20151214_1222'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='source_url',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
