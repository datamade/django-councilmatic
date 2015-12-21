# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('councilmatic_core', '0005_auto_20151215_1430'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='subject',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
