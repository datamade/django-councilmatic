# Custom migration
from __future__ import unicode_literals
import re

from django.conf import settings
from django.db import migrations, models

def unmangle_identifier(apps, schema_editor):
    '''
    The `fix_bill_id` function mangled NYC Bills in at least two ways:
    (1) removing zeroes, e.g., 'Res 0229-2004' (original) becomes 'Res 229-2004' (mangled)
    (2) adding a space, e.g., 'T2018-1245' (original) becomes 'T 2018-1245' (mangled).

    Note: the second case ONLY affected bills that begin with 'T', and the first case did NOT affect bills that begin with 'T' - that is, NYC bills never follow these patterns 'T 0023-2015' or 'T0023-2015'.
    '''
    Bill = apps.get_model('councilmatic_core', 'Bill')

    if settings.OCD_CITY_COUNCIL_ID == 'ocd-organization/0f63aae8-16fd-4d3c-b525-00747a482cf9':
        deleted_zeroes = r'^([A-Za-z]*\s)(\d{1,3})(-\d{4})$'
        for bill in Bill.objects.filter(identifier__iregex=deleted_zeroes):
            pattern = re.compile(deleted_zeroes)
            unmangled_identifier = pattern.sub(lambda match: match.group(1) + '{:0>4}'.format(match.group(2)) + match.group(3), bill.identifier)

            bill.identifier = unmangled_identifier
            bill.save()

        added_space = r'^([T]*\s)(\d{1,4}-\d{1,4})$'
        for bill in Bill.objects.filter(identifier__iregex=added_space):
            pattern = re.compile(added_space)
            unmangled_identifier = pattern.sub(lambda match: match.group(1).rstrip() + match.group(2), bill.identifier)

            bill.identifier = unmangled_identifier
            bill.save()


class Migration(migrations.Migration):
    dependencies = [
        ('councilmatic_core', '0036_auto_20180302_1247')
    ]

    operations = [
        migrations.RunPython(unmangle_identifier)
    ]