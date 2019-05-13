# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('councilmatic_core', '0006_bill_subject'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='division_ocd_id',
            field=models.CharField(max_length=255, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='post',
            name='shape',
            field=models.TextField(blank=True),
        ),
    ]
