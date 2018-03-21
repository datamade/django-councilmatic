# Custom migration
from __future__ import unicode_literals
import re

from django.db import migrations, models

def unmangle_identifier(apps, schema_editor):
    Bill = apps.get_model('councilmatic_core', 'Bill')
    # Bill = apps.get_model('nyc', 'NYCBill')

    _pattern = re.compile(r'([A-Za-z]*\s)(\d{1,3}-\d{4})$')

    for bill in Bill.objects.all():
        unmangled_identifier = _pattern.sub(lambda match: match.group(1) + ('0' * (9 - len(match.group(2)))) + match.group(2), bill.identifier)
        bill.identifier = unmangled_identifier
        bill.save()

class Migration(migrations.Migration):
    dependencies = [
        ('councilmatic_core', '0036_auto_20180302_1247')
    ]

    operations = [
        migrations.RunPython(unmangle_identifier)
    ]