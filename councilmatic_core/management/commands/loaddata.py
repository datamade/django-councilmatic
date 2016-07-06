from django.core.management.base import BaseCommand
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.text import slugify
from django.db.utils import IntegrityError, DataError
from django.db.models import Max
from councilmatic_core.models import Person, Bill, Organization, Action, ActionRelatedEntity, \
    Post, Membership, Sponsorship, LegislativeSession, \
    Document, BillDocument, Event, EventParticipant, EventDocument, \
    EventAgendaItem, AgendaItemBill

from dateutil import parser as date_parser

import requests
import json
import pytz
import re
import datetime
import psycopg2

for configuration in ['OCD_JURISDICTION_ID',
                      'HEADSHOT_PATH',
                      'LEGISLATIVE_SESSIONS'
                      ]:

    if not hasattr(settings, configuration):
        raise ImproperlyConfigured(
            'You must define {0} in settings.py'.format(configuration))

if not (hasattr(settings, 'OCD_CITY_COUNCIL_ID') or hasattr(settings, 'OCD_CITY_COUNCIL_NAME')):
    raise ImproperlyConfigured(
        'You must define a OCD_CITY_COUNCIL_ID or OCD_CITY_COUNCIL_NAME in settings.py')

app_timezone = pytz.timezone(settings.TIME_ZONE)

if hasattr(settings, 'OCDAPI_BASE_URL'):
    base_url = settings.OCDAPI_BASE_URL
else:
    base_url = 'http://ocd.datamade.us'

if hasattr(settings, 'BOUNDARY_API_BASE_URL'):
    bndry_base_url = settings.BOUNDARY_API_BASE_URL
else:
    bndry_base_url = base_url

DEBUG = settings.DEBUG


class Command(BaseCommand):
    help = 'loads in data from the open civic data API'
    update_since = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--endpoint', help="a specific endpoint to load data from")

        parser.add_argument('--delete',
                            action='store_true',
                            default=False,
                            help='deletes all data, and then loads all legislative sessions (by default, this task does not delete data & only loads new/updated data from current legislative session)')

        parser.add_argument('--update_since',
                            help='Only update objects in the database that have changed since this date')

    def handle(self, *args, **options):

        db_conn = settings.DATABASES['default']
        self.db_conn_kwargs = {
            'database': db_conn['NAME'],
            'user': db_conn['USER'],
            'password': db_conn['PASSWORD'],
            'host': db_conn['HOST'],
            'port': db_conn['PORT'],
        }

        if options['update_since']:
            self.update_since = date_parser.parse(options['update_since'])

        if options['endpoint'] == 'organizations':
            self.grab_organizations(delete=options['delete'])
            print("\ndone!", datetime.datetime.now())

        elif options['endpoint'] == 'bills':
            self.grab_bills(delete=options['delete'])
            print("\ndone!", datetime.datetime.now())

        elif options['endpoint'] == 'people':
            self.grab_people(delete=options['delete'])
            print("\ndone!", datetime.datetime.now())

        elif options['endpoint'] == 'events':
            self.grab_events(delete=options['delete'])
            print("\ndone!", datetime.datetime.now())

        else:
            print("\n** loading all data types! **\n")

            self.grab_organizations(delete=options['delete'])
            self.grab_people(delete=options['delete'])
            self.grab_bills(delete=options['delete'])
            self.grab_events(delete=options['delete'])

            print("\ndone!", datetime.datetime.now())

    def grab_organizations(self, delete=False):
        print("\n\nLOADING ORGANIZATIONS", datetime.datetime.now())
        if delete:
            with psycopg2.connect(**self.db_conn_kwargs) as conn:
                with conn.cursor() as curs:
                    curs.execute(
                        'TRUNCATE councilmatic_core_organization CASCADE')
                    curs.execute('TRUNCATE councilmatic_core_post CASCADE')
            print("deleted all organizations and posts")

        # first grab city council root
        if hasattr(settings, 'OCD_CITY_COUNCIL_ID'):
            self.grab_organization_posts({'id': settings.OCD_CITY_COUNCIL_ID})
        else:
            self.grab_organization_posts({'name': settings.OCD_CITY_COUNCIL_NAME})

        # this grabs a paginated listing of all organizations within a
        # jurisdiction
        orgs_url = base_url + '/organizations/?jurisdiction_id=' + \
            settings.OCD_JURISDICTION_ID
        r = requests.get(orgs_url)
        page_json = json.loads(r.text)

        for i in range(page_json['meta']['max_page']):

            r = requests.get(orgs_url + '&page=' + str(i + 1))
            page_json = json.loads(r.text)

            for result in page_json['results']:

                self.grab_organization_posts({'id': result['id']})

        # update relevant posts with shapes
        if hasattr(settings, 'BOUNDARY_SET') and settings.BOUNDARY_SET:
            self.populate_council_district_shapes()

    def grab_organization_posts(self, org_dict, parent=None):
        url = base_url + '/organizations/'
        r = requests.get(url, params=org_dict)
        page_json = json.loads(r.text)
        organization_ocd_id = page_json['results'][0]['id']

        url = base_url + '/' + organization_ocd_id + '/'
        r = requests.get(url)
        page_json = json.loads(r.text)

        if page_json.get('error'):
            raise DataError(page_json['error'])

        source_url = ''
        if page_json['sources']:
            source_url = page_json['sources'][0]['url']

        org_obj, created = Organization.objects.get_or_create(
            ocd_id=organization_ocd_id,
            name=page_json['name']
        )
        
        org_obj.classification = page_json['classification']
        org_obj.source_url = source_url
        org_obj._parent = parent
        org_obj.slug = slugify(page_json['name'])

        try:
            org_obj.save()
        except IntegrityError:
            # Slug must be unique
            ocd_id_part = organization_ocd_id.rsplit('-', 1)[1]
            org_obj.slug = slugify(page_json['name']) + ocd_id_part
            org_obj.save()

        # if created and DEBUG:
        #     print('   adding organization: %s' % org_obj.name )
        if created and DEBUG:
            print('\u263A', end=' ', flush=True)

        for post_json in page_json['posts']:

            try:
                obj = Post.objects.get(ocd_id=post_json['id'])

                obj.label = post_json['label']
                obj.role = post_json['role']
                obj._organization = org_obj
                obj.division_ocd_id = post_json['division_id']

                obj.save()

            except Post.DoesNotExist:
                obj, created = Post.objects.get_or_create(
                    ocd_id=post_json['id'],
                    label=post_json['label'],
                    role=post_json['role'],
                    _organization=org_obj,
                    division_ocd_id=post_json['division_id'],
                )

        for child in page_json['children']:
            self.grab_organization_posts({'id': child['id']}, org_obj)

    def populate_council_district_shapes(self):

        print("\n\npopulating boundaries: %s" % settings.BOUNDARY_SET)

        # grab boundary listing
        bndry_set_url = bndry_base_url + '/boundaries/' + settings.BOUNDARY_SET
        r = requests.get(bndry_set_url + '/?limit=0')
        page_json = json.loads(r.text)

        # loop through boundary listing
        for bndry_json in page_json['objects']:
            # grab boundary shape
            shape_url = bndry_base_url + bndry_json['url'] + 'shape'
            r = requests.get(shape_url)
            # update the right post(s) with the shape
            if 'ocd-division' in bndry_json['external_id']:
                division_ocd_id = bndry_json['external_id']
                Post.objects.filter(
                    division_ocd_id=division_ocd_id).update(shape=r.text)
            else:
                # Represent API doesn't use OCD id as external_id,
                # so we must work around that
                division_ocd_id_fragment = ':' + bndry_json['external_id']
                Post.objects.filter(
                    division_ocd_id__endswith=division_ocd_id_fragment).update(shape=r.text)

    def grab_people(self, delete=False):
        # find people associated with existing organizations & bills

        print("\n\nLOADING PEOPLE", datetime.datetime.now())
        if delete:
            with psycopg2.connect(**self.db_conn_kwargs) as conn:
                with conn.cursor() as curs:
                    curs.execute('TRUNCATE councilmatic_core_person CASCADE')
                    curs.execute(
                        'TRUNCATE councilmatic_core_membership CASCADE')
            print("deleted all people, memberships")

        # grab people associated with all existing organizations
        orgs = Organization.objects.exclude(
            name='Democratic').exclude(name='Republican').all()
        for organization in orgs:
            url = base_url + '/' + organization.ocd_id + '/'
            r = requests.get(url)
            page_json = json.loads(r.text)

            for membership_json in page_json['memberships']:
                self.grab_person_memberships(membership_json['person']['id'])

    def grab_bills(self, delete=False):
        # this grabs all bills & associated actions, documents from city council
        # organizations need to be populated before bills & actions are
        # populated

        print("\n\nLOADING BILLS", datetime.datetime.now())
        if delete:
            with psycopg2.connect(**self.db_conn_kwargs) as conn:
                with conn.cursor() as curs:
                    curs.execute('TRUNCATE councilmatic_core_bill CASCADE')
                    curs.execute('TRUNCATE councilmatic_core_action CASCADE')
                    curs.execute(
                        'TRUNCATE councilmatic_core_actionrelatedentity CASCADE')
                    curs.execute(
                        'TRUNCATE councilmatic_core_legislativesession CASCADE')
                    curs.execute('TRUNCATE councilmatic_core_document CASCADE')
                    curs.execute(
                        'TRUNCATE councilmatic_core_billdocument CASCADE')
                    curs.execute(
                        'TRUNCATE councilmatic_core_sponsorship CASCADE')
            print(
                "deleted all bills, actions, legislative sessions, documents, sponsorships\n")

        # get legislative sessions
        self.grab_legislative_sessions()

        if hasattr(settings, 'OCD_CITY_COUNCIL_ID'):
            query_params = {'from_organization__id': settings.OCD_CITY_COUNCIL_ID}
        else:
            query_params = {'from_organization__name': settings.OCD_CITY_COUNCIL_NAME}

        # grab all legislative sessions
        if self.update_since is None:
            max_updated = Bill.objects.all().aggregate(
                Max('ocd_updated_at'))['ocd_updated_at__max']

            if max_updated is None:
                max_updated = datetime.datetime(1900, 1, 1)
        else:
            max_updated = self.update_since

        query_params['sort'] = 'updated_at'
        query_params['updated_at__gte'] = max_updated.isoformat()

        print('grabbing bills since', query_params['updated_at__gte'])

        search_url = '{}/bills/'.format(base_url)
        search_results = requests.get(search_url, params=query_params)
        page_json = search_results.json()

        leg_session_obj = None

        for page_num in range(page_json['meta']['max_page']):

            query_params['page'] = int(page_num) + 1
            result_page = requests.get(search_url, params=query_params)

            for result in result_page.json()['results']:

                bill_url = '{base}/{bill_id}/'.format(
                    base=base_url, bill_id=result['id'])
                bill_detail = requests.get(bill_url)

                leg_session_id = bill_detail.json()['legislative_session'][
                    'identifier']

                if leg_session_obj is None:
                    leg_session_obj = LegislativeSession.objects.get(
                        identifier=leg_session_id)

                elif leg_session_obj.identifier != leg_session_id:
                    leg_session_obj = LegislativeSession.objects.get(
                        identifier=leg_session_id)

                self.grab_bill(bill_detail.json(), leg_session_obj)

    def grab_legislative_sessions(self):
        session_ids = []

        if hasattr(settings, 'LEGISLATIVE_SESSIONS') and settings.LEGISLATIVE_SESSIONS:
            session_ids = settings.LEGISLATIVE_SESSIONS
        else:
            url = base_url + '/' + settings.OCD_JURISDICTION_ID + '/'
            r = requests.get(url)
            page_json = json.loads(r.text)
            session_ids = [session['identifier']
                           for session in page_json['legislative_sessions']]

        # Sort so most recent session last
        session_ids.sort()
        for leg_session in session_ids:
            obj, created = LegislativeSession.objects.get_or_create(
                identifier=leg_session,
                jurisdiction_ocd_id=settings.OCD_JURISDICTION_ID,
                name='%s Legislative Session' % leg_session,
            )
            if created and DEBUG:
                print('adding legislative session: %s' % obj.name)

    def grab_bill(self, page_json, leg_session_obj):

        from_org = Organization.objects.get(
            ocd_id=page_json['from_organization']['id'])

        if page_json['extras'].get('local_classification'):
            bill_type = page_json['extras']['local_classification']

        elif len(page_json['classification']) == 1:
            bill_type = page_json['classification'][0]

        else:
            raise Exception(page_json['classification'])

        if 'full_text' in page_json['extras']:
            full_text = page_json['extras']['full_text']

        else:
            full_text = ''

        if 'ocr_full_text' in page_json['extras']:
            ocr_full_text = page_json['extras']['ocr_full_text']
        elif 'plain_text' in page_json['extras']:
            ocr_full_text = page_json['extras']['plain_text']
        else:
            ocr_full_text = ''

        if 'subject' in page_json and page_json['subject']:
            subject = page_json['subject'][0]
        else:
            subject = ''

        if page_json['abstracts']:
            abstract = page_json['abstracts'][0]['abstract']
        else:
            abstract = ''

        source_url = ''
        for source in page_json['sources']:
            if source['note'] == 'web':
                source_url = source['url']

        bill_id = page_json['id']

        bill_fields = {
            'ocd_id': bill_id,
            'ocd_created_at': page_json['created_at'],
            'ocd_updated_at': page_json['updated_at'],
            'description': page_json['title'],
            'identifier': page_json['identifier'],
            'classification': page_json['classification'][0],
            'source_url': source_url,
            'source_note': page_json['sources'][0]['note'],
            '_from_organization': from_org,
            'full_text': full_text,
            'ocr_full_text': ocr_full_text,
            'abstract': abstract,
            '_legislative_session': leg_session_obj,
            'bill_type': bill_type,
            'subject': subject,
        }

        updated = False
        created = False
        # look for existing bill
        try:
            obj = Bill.objects.get(ocd_id=bill_id)

            obj.ocd_created_at = page_json['created_at']
            obj.ocd_updated_at = page_json['updated_at']
            obj.description = page_json['title']
            obj.identifier = page_json['identifier']
            obj.classification = page_json['classification'][0]
            obj.source_url = source_url
            obj.source_note = page_json['sources'][0]['note']
            obj._from_organization = from_org
            obj.full_text = full_text
            obj.ocr_full_text = ocr_full_text
            obj.abstract = abstract
            obj._legislative_session = leg_session_obj
            obj.bill_type = bill_type
            obj.subject = subject

            obj.save()
            updated = True

            if DEBUG:
                print('\u270E', end=' ', flush=True)

        # except if it doesn't exist, we need to make it
        except Bill.DoesNotExist:

            try:
                bill_fields['slug'] = slugify(page_json['identifier'])
                obj, created = Bill.objects.get_or_create(**bill_fields)

            except IntegrityError:
                ocd_id_part = bill_id.rsplit('-', 1)[1]
                bill_fields['slug'] = slugify(
                    page_json['identifier']) + ocd_id_part
                obj, created = Bill.objects.get_or_create(**bill_fields)

            if created and DEBUG:
                print('\u263A', end=' ', flush=True)

        if created or updated:

            if updated:
                # delete existing bill actions, sponsorships, billdocuments
                obj.actions.all().delete()
                obj.sponsorships.all().delete()
                obj.documents.all().delete()

            # update actions for a bill
            action_order = 0
            for action_json in page_json['actions']:
                self.load_action(action_json, obj, action_order)
                action_order += 1

            # update bill last_action_date with most recent action
            obj.last_action_date = obj.get_last_action_date()
            obj.save()

            # update documents for with a bill (attachments & versions)
            # attachments are related files
            for document_json in page_json['documents']:
                self.load_bill_attachment(document_json, obj)
            # versions are the bill itself
            for document_json in page_json['versions']:
                self.load_bill_version(document_json, obj)

            # update sponsorships for a bill
            for sponsor_json in page_json['sponsorships']:
                self.load_bill_sponsorship(sponsor_json, obj)

    def load_bill_sponsorship(self, sponsor_json, bill):

        # if the sponsor is a city council member, it has alread been loaded in
        # grab_people
        if sponsor_json['entity_id'] and sponsor_json['entity_type'] == 'person':
            sponsor = Person.objects.filter(
                ocd_id=sponsor_json['entity_id']).first()
        # otherwise, it is probably the mayor, or city clerk, or an org
        # in which case, we may have to make a person
        # non city council members will not have an ocd id or slug - just name
        # (we might want to handle mayor differently?)
        else:
            sponsor, created = Person.objects.get_or_create(
                ocd_id=None,
                name=sponsor_json['entity_name'],
                headshot='',
                source_url='',
                source_note='',
                website_url='',
                email='',
                slug=None,
            )

        if sponsor:
            obj, created = Sponsorship.objects.get_or_create(
                _bill=bill,
                _person=sponsor,
                classification=sponsor_json['classification'],
                is_primary=sponsor_json['primary'],
            )
        else:
            # TEMPORARY - remove this when mayor/clerk stuff is fixed
            print("**SPONSOR MISSING FROM PEOPLE**")
            print(sponsor_json)
            print(bill.ocd_id)

    def load_action(self, action_json, bill, action_order):

        org = Organization.objects.filter(
            ocd_id=action_json['organization']['id']).first()

        classification = ""
        if action_json['classification']:
            classification = action_json['classification'][0]

        action_date = app_timezone.localize(
            date_parser.parse(action_json['date']))

        action_obj, created = Action.objects.get_or_create(
            date=action_date,
            classification=classification,
            description=action_json['description'],
            _organization=org,
            _bill=bill,
            order=action_order,
        )

        # if created and DEBUG:
        #     print('      adding action: %s' %action_json['description'])

        for related_entity_json in action_json['related_entities']:

            action_related_entity = {
                '_action': action_obj,
                'entity_name': related_entity_json['name'],
                'entity_type': related_entity_json['entity_type'],
                'organization_ocd_id': '',
                'person_ocd_id': '',
            }

            if related_entity_json['entity_type'] == 'organization':

                if not related_entity_json['organization_id']:
                    org = Organization.objects.filter(
                        name=action_related_entity['entity_name']).first()
                    if org:
                        action_related_entity[
                            'organization_ocd_id'] = org.ocd_id
                    else:
                        print("\n\n" + "-" * 60)
                        print("WARNING: ORGANIZATION NOT FOUND %s" %
                              action_related_entity['entity_name'])
                        print("cannot find related entity for bill %s" %
                              bill.ocd_id)
                        print("-" * 60 + "\n")

                else:
                    action_related_entity[
                        'organization_ocd_id'] = related_entity_json['organization_id']

            elif related_entity_json['entity_type'] == 'person':

                if not related_entity_json['person_id']:
                    org = Person.objects.filter(name=action_related_entity[
                                                'entity_name']).first()
                    if org:
                        action_related_entity['person_ocd_id'] = org.ocd_id
                    else:
                        raise Exception('person called {0} does not exist'
                                        .format(action_related_entity['entity_name']))
                else:
                    action_related_entity[
                        'person_ocd_id'] = related_entity_json['person_id']

            if org:
                obj, created = ActionRelatedEntity.objects.get_or_create(
                    **action_related_entity)

            # if created and DEBUG:
            #     print('         adding related entity: %s' %obj.entity_name)

    def load_bill_attachment(self, document_json, bill):

        doc_obj, created = Document.objects.get_or_create(
            note=document_json['note'],
            url=document_json['links'][0]['url'],
        )

        obj, created = BillDocument.objects.get_or_create(
            bill=bill,
            document=doc_obj,
            document_type='A',
        )

    def load_bill_version(self, document_json, bill):

        doc_obj, created = Document.objects.get_or_create(
            note=document_json['note'],
            url=document_json['links'][0]['url'],
        )

        obj, created = BillDocument.objects.get_or_create(
            bill=bill,
            document=doc_obj,
            document_type='V',
        )

    def grab_person_memberships(self, person_id):
        # this grabs a person and all their memberships
        
        url = base_url + '/' + person_id + '/'
        r = requests.get(url)
        page_json = json.loads(r.text)

        # TO DO: handle updating people & memberships
        person = Person.objects.filter(ocd_id=person_id).first()
        if not person:

            # save image to disk
            if page_json['image']:
                r = requests.get(page_json['image'], verify=False)
                if r.status_code == 200:
                    with open((settings.HEADSHOT_PATH + page_json['id'] + ".jpg"), 'wb') as f:
                        for chunk in r.iter_content(1000):
                            f.write(chunk)
                            f.flush()

            email = ''
            for contact_detail in page_json['contact_details']:
                if contact_detail['type'] == 'email':
                    if contact_detail['value'] != 'mailto:':
                        email = contact_detail['value']

            website_url = ''
            for link in page_json['links']:
                if link['note'] == "web site":
                    website_url = link['url']

            try:
                person = Person.objects.create(
                    ocd_id=page_json['id'],
                    name=page_json['name'],
                    headshot=page_json['image'],
                    source_url=page_json['sources'][0]['url'],
                    source_note=page_json['sources'][0]['note'],
                    website_url=website_url,
                    email=email,
                    slug=slugify(page_json['name']),
                )
            except IntegrityError:
                ocd_id_part = page_json['id'].rsplit('-', 1)[1]
                person = Person.objects.create(
                    ocd_id=page_json['id'],
                    name=page_json['name'],
                    headshot=page_json['image'],
                    source_url=page_json['sources'][0]['url'],
                    source_note=page_json['sources'][0]['note'],
                    website_url='',
                    email=email,
                    slug=slugify(page_json['name']) + ocd_id_part,
                )

            # if DEBUG:
            #     print('   adding person: %s' % person.name)
            if DEBUG:
                print('\u263A', end=' ', flush=True)

        for membership_json in page_json['memberships']:

            if membership_json['post']:
                post = Post.objects.filter(ocd_id=membership_json[
                                           'post']['id']).first()
            else:
                post = None

            organization = Organization.objects.filter(
                ocd_id=membership_json['organization']['id']).first()
            # adding republican or democratic party when encountered
            # b/c parties are not added when organizations are loaded (in
            # grab_organizations)
            if not organization and membership_json['organization']['name'] in ['Republican', 'Democratic']:
                self.grab_organization_posts({'id': membership_json['organization']['id']})
                organization = Organization.objects.filter(
                    ocd_id=membership_json['organization']['id']).first()

            try:
                end_date = parse_date(membership_json['end_date'])
            except:
                end_date = None
            try:
                start_date = parse_date(membership_json['start_date'])
            except:
                start_date = None
            
            try:

                obj = Membership.objects.get(
                            _organization=organization,
                            _person=person,
                            _post=post)
                created = False
                
                obj.label = membership_json['label']
                obj.role = membership_json['role']
                obj.start_date = start_date
                obj.end_date = end_date
                obj.save()
            
            except Membership.DoesNotExist:
                obj = Membership.objects.create(
                            _organization=organization,
                            _person=person,
                            _post=post,
                            label=membership_json['label'],
                            role=membership_json['role'],
                            start_date=start_date,
                            end_date=end_date)
                created = True
            except Membership.MultipleObjectsReturned:
                memberships = Membership.objects.filter(
                                _organization=organization,
                                _post=post,
                                _person=person)

                for membership in memberships[1:]:
                    membership.delete()
                
                obj = Membership.objects.get(
                            _organization=organization,
                            _person=person,
                            _post=post)
                created = False
                
                obj.label = membership_json['label']
                obj.role = membership_json['role']
                obj.start_date = start_date
                obj.end_date = end_date
                obj.save()


            # if created and DEBUG:
            #     print('      adding membership: %s' % obj.role)

    def grab_events(self, delete=False):

        print("\n\nLOADING EVENTS", datetime.datetime.now())
        if delete:
            with psycopg2.connect(**self.db_conn_kwargs) as conn:
                with conn.cursor() as curs:
                    curs.execute('TRUNCATE councilmatic_core_event CASCADE')
                    curs.execute(
                        'TRUNCATE councilmatic_core_eventparticipant CASCADE')
                    curs.execute(
                        'TRUNCATE councilmatic_core_eventdocument CASCADE')
                    curs.execute(
                        'TRUNCATE councilmatic_core_eventagendaitem CASCADE')
                    curs.execute(
                        'TRUNCATE councilmatic_core_agendaitembill CASCADE')
            print(
                "deleted all events, participants, documents, agenda items, agenda item bill references")

        # this grabs a paginated listing of all events within a jurisdiction
        events_url = base_url + '/events/?jurisdiction_id=' + settings.OCD_JURISDICTION_ID
        r = requests.get(events_url)
        page_json = json.loads(r.text)

        for i in range(page_json['meta']['max_page']):

            r = requests.get(events_url + '&page=' + str(i + 1))
            page_json = json.loads(r.text)

            for result in page_json['results']:
                self.grab_event(result['id'])

    def grab_event(self, event_ocd_id):

        event_url = base_url + '/' + event_ocd_id + '/'
        r = requests.get(event_url)

        if r.status_code == 200:
            page_json = json.loads(r.text)

            try:
                legistar_id = re.findall(
                    'ID=(.*)&GUID', page_json['sources'][0]['url'])[0]
            except IndexError:
                print("\n\n" + "-" * 60)
                print("WARNING: MISSING SOURCE %s" % event_ocd_id)
                print("event has no source")
                print("-" * 60 + "\n")
                legistar_id = event_ocd_id

            event_fields = {
                'ocd_id': event_ocd_id,
                'ocd_created_at': page_json['created_at'],
                'ocd_updated_at': page_json['updated_at'],
                'name': page_json['name'],
                'description': page_json['description'],
                'classification': page_json['classification'],
                'start_time': parse_datetime(page_json['start_time']),
                'end_time': parse_datetime(page_json['end_time']) if page_json['end_time'] else None,
                'all_day': page_json['all_day'],
                'status': page_json['status'],
                'location_name': page_json['location']['name'],
                'location_url': page_json['location']['url'],
                'source_url': page_json['sources'][0]['url'],
                'source_note': page_json['sources'][0]['note'],
            }

            updated = False
            created = False

            # look for existing event
            try:
                event_obj = Event.objects.get(ocd_id=event_ocd_id)
                # check if it has been updated on api
                # TO-DO: fix date comparison to handle timezone naive times
                # from api
                if event_obj.ocd_updated_at.isoformat() != page_json['updated_at']:

                    event_obj.ocd_created_at = page_json['created_at']
                    event_obj.ocd_updated_at = page_json['updated_at']
                    event_obj.name = page_json['name']
                    event_obj.description = page_json['description']
                    event_obj.classification = page_json['classification']
                    event_obj.start_time = parse_datetime(
                        page_json['start_time'])
                    event_obj.end_time = parse_datetime(page_json['end_time']) if page_json[
                        'end_time'] else None
                    event_obj.all_day = page_json['all_day']
                    event_obj.status = page_json['status']
                    event_obj.location_name = page_json['location']['name']
                    event_obj.location_url = page_json['location']['url']
                    event_obj.source_url = page_json['sources'][0]['url']
                    event_obj.source_note = page_json['sources'][0]['note']

                    event_obj.save()
                    updated = True

                    if DEBUG:
                        print('\u270E', end=' ', flush=True)

            # except if it doesn't exist, we need to make it
            except Event.DoesNotExist:
                try:
                    event_fields['slug'] = legistar_id
                    event_obj, created = Event.objects.get_or_create(
                        **event_fields)

                except IntegrityError:
                    event_fields['slug'] = event_ocd_id
                    event_obj, created = Event.objects.get_or_create(
                        **event_fields)
                    print("\n\n" + "-" * 60)
                    print("WARNING: SLUG ALREADY EXISTS FOR %s" % event_ocd_id)
                    print("legistar id (what slug should be): %s" % legistar_id)
                    print("using ocd id as slug instead")
                    print("-" * 60 + "\n")

                # if created and DEBUG:
                #     print('   adding event: %s' % event_ocd_id)
                if created and DEBUG:
                    print('\u263A', end=' ', flush=True)
                    print(event_obj.ocd_id)

            if created or updated:

                if updated:
                    # delete existing participants, documents, agenda items
                    event_obj.participants.all().delete()
                    event_obj.documents.all().delete()
                    event_obj.agenda_items.all().delete()

                for participant_json in page_json['participants']:
                    obj, created = EventParticipant.objects.get_or_create(
                        event=event_obj,
                        note=participant_json['note'],
                        entity_name=participant_json['entity_name'],
                        entity_type=participant_json['entity_type']
                    )
                    # if created and DEBUG:
                    #     print('      adding participant: %s' %obj.entity_name)

                for document_json in page_json['documents']:
                    self.load_eventdocument(document_json, event_obj)

                for agenda_item_json in page_json['agenda']:
                    self.load_eventagendaitem(agenda_item_json, event_obj)

        else:
            print("\n\n" + "*" * 60)
            print("SKIPPING EVENT %s" % event_ocd_id)
            print("cannot retrieve event data")
            print("*" * 60 + "\n")

    def load_eventagendaitem(self, agenda_item_json, event):

        agendaitem_obj, created = EventAgendaItem.objects.get_or_create(
            event=event,
            order=agenda_item_json['order'],
            description=agenda_item_json['description'],
        )

        # if created and DEBUG:
        #     print('      adding agenda item: %s' %agendaitem_obj.order)

        if agenda_item_json['related_entities']:
            related_entity_json = agenda_item_json['related_entities'][0]
            clean_bill_identifier = re.sub(
                ' 0', ' ', related_entity_json['entity_name'])
            related_bill = Bill.objects.filter(
                identifier=clean_bill_identifier).first()

            if related_bill:
                obj, created = AgendaItemBill.objects.get_or_create(
                    agenda_item=agendaitem_obj,
                    bill=related_bill,
                    note=related_entity_json['note'],
                )

            # if created and DEBUG:
            #     print('         adding related bill: %s' %related_bill.identifier)

    def load_eventdocument(self, document_json, event):
        
        try:
            doc_obj, created = Document.objects.get_or_create(
                note=document_json['note'],
                url=document_json['links'][0]['url']
            )
        except Document.MultipleObjectsReturned:
            documents = Document.objects.filter(
                note=document_json['note'],
                url=document_json['links'][0]['url']
            )

            for document in documents[1:]:
                document.delete()
            
            doc_obj = Document.objects.get(
                note=document_json['note'],
                url=document_json['links'][0]['url']
            )
            created = False

        obj, created = EventDocument.objects.get_or_create(
            event=event,
            document=doc_obj,
        )

        # if created and DEBUG:
        #     print('      adding document: %s' % doc_obj.note)
