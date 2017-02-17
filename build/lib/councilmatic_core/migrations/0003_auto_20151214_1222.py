# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('councilmatic_core', '0002_auto_20151210_1342'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bill',
            name='ocd_updated_at',
            field=models.DateTimeField(default=None),
        ),
        migrations.AlterField(
            model_name='person',
            name='ocd_id',
            field=models.CharField(unique=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='person',
            name='slug',
            field=models.CharField(unique=True, max_length=255, null=True),
        ),
    ]
