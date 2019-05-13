# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('councilmatic_core', '0004_auto_20151214_1413'),
    ]

    operations = [
        migrations.AddField(
            model_name='billdocument',
            name='document_type',
            field=models.CharField(max_length=255, choices=[(
                'A', 'Attachment'), ('V', 'Version')], default='A'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='document',
            name='full_text',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='document',
            name='url',
            field=models.TextField(blank=True),
        ),
    ]
