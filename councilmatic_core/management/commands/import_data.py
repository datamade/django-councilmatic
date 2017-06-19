# -*- coding=utf-8 -*-

import json
import re
import datetime
import os
import sys
import logging
import logging.config

import requests
import pytz
import psycopg2
import sqlalchemy as sa

from requests.packages.urllib3.exceptions import InsecureRequestWarning

from dateutil import parser as date_parser

from django.core.management.base import BaseCommand
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.text import slugify, Truncator
from django.db.utils import IntegrityError, DataError
from django.db.models import Max

from councilmatic_core.models import Person, Bill, Organization, Action, ActionRelatedEntity, \
    Post, Membership, Sponsorship, LegislativeSession, \
    Document, BillDocument, Event, EventParticipant, EventDocument, \
    EventAgendaItem


logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

session = requests.Session()

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

DB_CONN = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'

engine = sa.create_engine(DB_CONN.format(**settings.DATABASES['default']),
                          convert_unicode=True,
                          server_side_cursors=True)

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
            '--endpoints',
            help="a specific endpoint to load data from",
            default='organizations,people,bills,events')

        parser.add_argument('--delete',
                            action='store_true',
                            default=False,
                            help='deletes all data, and then loads all legislative sessions (by default, this task does not delete data & only loads new/updated data from current legislative session)')

        parser.add_argument('--update_since',
                            help='Only update objects in the database that have changed since this date')

        parser.add_argument('--import_only',
                            action='store_true',
                            default=False,
                            help='Load already downloaded OCD data')

        parser.add_argument('--download_only',
                            action='store_true',
                            default=False,
                            help='Only download OCD data')

        parser.add_argument('--no_index',
                            action='store_true',
                            default=False,
                            help='Only download OCD data')


    def handle(self, *args, **options):

        self.connection = engine.connect()

        self.downloads_folder = 'downloads'
        self.this_folder = os.path.abspath(os.path.dirname(__file__))

        self.organizations_folder = os.path.join(self.downloads_folder, 'organizations')
        self.posts_folder = os.path.join(self.downloads_folder, 'posts')
        self.bills_folder = os.path.join(self.downloads_folder, 'bills')
        self.people_folder = os.path.join(self.downloads_folder, 'people')
        self.events_folder = os.path.join(self.downloads_folder, 'events')

        if options['update_since']:
            self.update_since = date_parser.parse(options['update_since'])

        endpoints = options['endpoints'].split(',')

        for endpoint in endpoints:

            if endpoint not in ['organizations', 'people', 'bills', 'events']:

                self.log_message('"{}" is not a valid endpoint'.format(endpoint), style='ERROR')

            else:

                download_only = options['download_only']
                import_only = options['import_only']

                if not import_only and not download_only:
                    download_only = True
                    import_only = True

                try:
                    etl_method = getattr(self, '{}_etl'.format(endpoint))
                    etl_method(import_only=import_only,
                               download_only=download_only,
                               delete=options['delete'])

                except Exception as e:
                    logger.error(e, exc_info=True)


        if not options['no_index'] and getattr(settings, 'USING_NOTIFICATIONS', None):
            from django.core import management

            try:
                management.call_command('update_index', age=24)
            except Exception as e:
                logger.error(e, exc_info=True)

            try:
                management.call_command('send_notifications')
            except Exception as e:
                logger.error(e, exc_info=True)


    def log_message(self,
                    message,
                    fancy=False,
                    style='HTTP_SUCCESS',
                    art_file=None,
                    center=False,
                    timestamp=True):

        if timestamp:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message = '{0} {1}'.format(now, message)

        if len(message) < 70 and center:
            padding = (70 - len(message)) / 2
            message = '{0}{1}{0}'.format(' ' * int(padding), message)

        if fancy and not art_file:
            thing_count = len(message) + 2

            message = '\n{0}\n  {1}  \n{0}'.format('-' * 70, message)

        elif art_file:
            art = open(os.path.join(self.this_folder, 'art', art_file)).read()
            message = '\n{0} \n {1}'.format(art, message)

        style = getattr(self.style, style)
        self.stdout.write(style('{}\n'.format(message)))

    def organizations_etl(self,
                          import_only=True,
                          download_only=True,
                          delete=False):

        if download_only:
            self.log_message('Downloading organizations ...',
                             center=True,
                             art_file='organizations.txt')

            self.grab_organizations()

        if import_only:
            self.log_message('Importing organizations ...',
                             center=True,
                             art_file='organizations.txt')

            self.insert_raw_organizations(delete=delete)
            self.insert_raw_posts(delete=delete)

            self.update_existing_organizations()
            self.update_existing_posts()

            self.add_new_organizations()
            self.add_new_posts()

        self.log_message('Organizations Complete!',
                         fancy=True,
                         center=True,
                         style='SUCCESS')

    def people_etl(self,
                   import_only=False,
                   download_only=False,
                   delete=False):

        if download_only:
            self.log_message('Downloading people ...',
                             center=True,
                             art_file='people.txt')

            self.grab_people()

        if import_only:

            self.log_message('Importing people ...',
                             center=True,
                             art_file='people.txt')

            self.insert_raw_people(delete=delete)
            self.insert_raw_memberships(delete=delete)

            self.update_existing_people()
            self.update_existing_memberships()

            self.add_new_people()
            self.add_new_memberships()

        self.log_message('People Complete!',
                         fancy=True,
                         center=True,
                         style='SUCCESS')

    def bills_etl(self,
                  import_only=False,
                  download_only=False,
                  delete=False):

        self.create_legislative_sessions()

        if download_only:
            self.log_message('Downloading bills ...',
                             center=True,
                             art_file='bills.txt')
            self.grab_bills()

        if import_only:
            self.log_message('Importing bills ...',
                             center=True,
                             art_file='bills.txt')
            self.insert_raw_bills(delete=delete)
            self.insert_raw_actions(delete=delete)

            self.update_existing_bills()
            self.update_existing_actions()

            self.add_new_bills()
            self.add_new_actions()

            self.insert_raw_action_related_entity(delete=delete)
            self.insert_raw_sponsorships(delete=delete)
            self.insert_raw_billdocuments(delete=delete)

            self.update_existing_action_related_entity()
            self.update_existing_sponsorships()
            self.update_existing_billdocuments()

            self.add_new_action_related_entity()
            self.add_new_sponsorships()
            self.add_new_billdocuments()

        self.log_message('Bills Complete!', fancy=True, style='SUCCESS', center=True)

    def events_etl(self,
                   import_only=False,
                   download_only=False,
                   delete=False):

        if download_only:
            self.log_message('Downloading events ...',
                             center=True,
                             fancy=True)
            self.grab_events()

        if import_only:
            self.log_message('Importing events ...',
                             center=True,
                             fancy=True)
            self.insert_raw_events(delete=delete)
            self.insert_raw_eventparticipants(delete=delete)
            self.insert_raw_eventdocuments(delete=delete)
            self.insert_raw_event_agenda_items(delete=delete)

            self.update_existing_events()
            self.update_existing_eventparticipants()
            self.update_existing_eventdocuments()
            self.update_existing_event_agenda_items()

            self.add_new_events()
            self.add_new_eventparticipants()
            self.add_new_eventdocuments()
            self.add_new_event_agenda_items()

        self.log_message('Events Complete!', fancy=True, style='SUCCESS', center=True)

    #########################
    ###                   ###
    ### DOWNLOAD FROM OCD ###
    ###                   ###
    #########################

    def grab_organizations(self):
        os.makedirs(self.organizations_folder, exist_ok=True)
        os.makedirs(self.posts_folder, exist_ok=True)

        # first grab city council root
        if hasattr(settings, 'OCD_CITY_COUNCIL_ID'):
            self.grab_organization_posts({'id': settings.OCD_CITY_COUNCIL_ID})
        else:
            self.grab_organization_posts({'name': settings.OCD_CITY_COUNCIL_NAME})

        orgs_url = '{}/organizations/?sort=updated_at&jurisdiction_id={}'.format(base_url, settings.OCD_JURISDICTION_ID)
        r = session.get(orgs_url)

        page_json = json.loads(r.text)

        org_counter = 0
        post_counter = 0

        for i in range(page_json['meta']['max_page']):

            r = session.get(orgs_url + '&page=' + str(i + 1))
            page_json = json.loads(r.text)

            org_counter += len(page_json['results'])

            for result in page_json['results']:

                post_count = self.grab_organization_posts({'id': result['id']})

                post_counter += post_count

                print('.', end='')
                sys.stdout.flush()

        print('\n')
        self.log_message('Downloaded {0} orgs and {1} posts'.format(org_counter, post_counter))

        # update relevant posts with shapes
        if hasattr(settings, 'BOUNDARY_SET') and settings.BOUNDARY_SET:
            self.populate_council_district_shapes()

    def grab_organization_posts(self, org_dict):
        url = base_url + '/organizations/'

        r = session.get(url, params=org_dict)
        page_json = json.loads(r.text)
        organization_ocd_id = page_json['results'][0]['id']

        url = base_url + '/' + organization_ocd_id + '/'
        r = session.get(url)
        page_json = json.loads(r.text)

        if page_json.get('error'):
            raise DataError(page_json['error'])

        ocd_uuid = org_dict['id'].split('/')[-1]
        organization_filename = '{}.json'.format(ocd_uuid)

        with open(os.path.join(self.organizations_folder, organization_filename), 'w') as f:
            f.write(json.dumps(page_json))


        for post_json in page_json['posts']:

            post_uuid = post_json['id'].split('/')[-1]
            post_filename = '{}.json'.format(post_uuid)
            post_json['org_ocd_id'] = org_dict['id']

            with open(os.path.join(self.posts_folder, post_filename), 'w') as f:
                f.write(json.dumps(post_json))

        return len(page_json['posts'] + page_json['children'])

    def grab_people(self):
        # find people associated with existing organizations & bills

        os.makedirs(self.people_folder, exist_ok=True)

        seen_person = set()
        counter = 0
        for organization_json in os.listdir(self.organizations_folder):

            org_info = json.load(open(os.path.join(self.organizations_folder, organization_json)))

            for membership_json in org_info['memberships']:
                person_id = membership_json['person']['id']
                if person_id in seen_person:
                    continue

                seen_person.add(person_id)
                person_json = self.grab_person_memberships(person_id)

                person_uuid = person_json['id'].split('/')[-1]
                person_filename = '{}.json'.format(person_uuid)

                with open(os.path.join(self.people_folder, person_filename), 'w') as f:
                    f.write(json.dumps(person_json))

                print('.', end='')
                sys.stdout.flush()

                counter += 1

        self.log_message('Downloaded {} people and memeberships'.format(counter), fancy=True)

    def grab_person_memberships(self, person_id):
        # this grabs a person and all their memberships

        url = base_url + '/' + person_id + '/'
        r = session.get(url)
        page_json = json.loads(r.text)

        # save image to disk
        if page_json['image']:
            r = session.get(page_json['image'], verify=False)
            if r.status_code == 200:
                with open((settings.HEADSHOT_PATH + page_json['id'] + ".jpg"), 'wb') as f:
                    for chunk in r.iter_content(1000):
                        f.write(chunk)
                        f.flush()

        page_json['email'] = None
        for contact_detail in page_json['contact_details']:
            if contact_detail['type'] == 'email':
                if contact_detail['value'] != 'mailto:':
                    page_json['email'] = contact_detail['value']

        page_json['website_url'] = None
        for link in page_json['links']:
            if link['note'] == "web site":
                page_json['website_url'] = link['url']

        return page_json

    def grab_bills(self):

        os.makedirs(self.bills_folder, exist_ok=True)

        if hasattr(settings, 'OCD_CITY_COUNCIL_ID'):
            query_params = {'from_organization__id': settings.OCD_CITY_COUNCIL_ID}
        else:
            query_params = {'from_organization__name': settings.OCD_CITY_COUNCIL_NAME}

        if self.update_since is None:
            max_updated = Bill.objects.all().aggregate(Max('ocd_updated_at'))['ocd_updated_at__max']

            if max_updated is None:
                max_updated = datetime.datetime(1900, 1, 1)
        else:
            max_updated = self.update_since

        query_params['sort'] = 'updated_at'
        query_params['updated_at__gte'] = max_updated.isoformat()

        self.log_message('Getting bills since {}'.format(query_params['updated_at__gte']), style='NOTICE')

        search_url = '{}/bills/'.format(base_url)
        search_results = session.get(search_url, params=query_params)
        page_json = search_results.json()

        counter = 0
        for page_num in range(page_json['meta']['max_page']):

            query_params['page'] = int(page_num) + 1
            result_page = session.get(search_url, params=query_params)

            for result in result_page.json()['results']:

                bill_url = '{base}/{bill_id}/'.format(
                    base=base_url, bill_id=result['id'])
                bill_detail = session.get(bill_url)

                bill_json = bill_detail.json()
                ocd_uuid = bill_json['id'].split('/')[-1]
                bill_filename = '{}.json'.format(ocd_uuid)

                with open(os.path.join(self.bills_folder, bill_filename), 'w') as f:
                    f.write(json.dumps(bill_json))

                counter += 1

                print('.', end='')
                sys.stdout.flush()

                if counter % 1000 == 0:
                    print('\n')
                    self.log_message('Downloaded {} bills'.format(counter))

        self.log_message('Downloaded {} bills'.format(counter), fancy=True)

    def grab_events(self):

        os.makedirs(self.events_folder, exist_ok=True)

        events_url = '{0}/events/'.format(base_url)

        params = {'jurisdiction_id': settings.OCD_JURISDICTION_ID}

        if self.update_since is None:
            max_updated = Event.objects.all().aggregate(
                Max('ocd_updated_at'))['ocd_updated_at__max']

            if max_updated is None:
                max_updated = datetime.datetime(1900, 1, 1)
        else:
            max_updated = self.update_since

        params['updated_at__gte'] = max_updated.isoformat()
        params['sort'] = 'updated_at'

        r = session.get(events_url, params=params)
        page_json = json.loads(r.text)

        counter = 0
        for i in range(page_json['meta']['max_page']):

            params['page'] = str(i + 1)
            r = session.get(events_url, params=params)
            page_json = json.loads(r.text)

            for event in page_json['results']:

                ocd_uuid = event['id'].split('/')[-1]
                event_filename = '{}.json'.format(ocd_uuid)

                event_url = base_url + '/' + event['id'] + '/'
                r = session.get(event_url)

                if r.status_code == 200:
                    page_json = json.loads(r.text)

                    with open(os.path.join(self.events_folder, event_filename), 'w') as f:
                        f.write(json.dumps(page_json))

                    counter += 1

                    print('.', end='')
                    sys.stdout.flush()

                    if counter % 1000 == 0:
                        print('\n')
                        self.log_message('Downloaded {} events'.format(counter))
                else:
                    self.log_message('Skipping event {} (cannot retrieve event data)'.format(event['id']), style='ERROR')

        self.log_message('Downloaded {} events'.format(counter), fancy=True)

    ###########################
    ###                     ###
    ### INSERT RAW ENTITIES ###
    ###                     ###
    ###########################

    def remake_raw(self, entity_type, delete=False):

        if delete:
            self.executeTransaction(
                'TRUNCATE councilmatic_core_{} CASCADE'.format(entity_type))

            print("deleted all {}".format(entity_type))

        self.executeTransaction('DROP TABLE IF EXISTS raw_{}'.format(entity_type))

        self.executeTransaction('''
            CREATE TABLE raw_{0} AS (
              SELECT * FROM councilmatic_core_{0}
            ) WITH NO DATA
        '''.format(entity_type))

    def setup_raw(self,
                  entity_type,
                  delete=False,
                  pk_cols=['ocd_id'],
                  updated_at=True):

        self.remake_raw(entity_type, delete=delete)

        if pk_cols:
            self.executeTransaction('''
                ALTER TABLE raw_{0} ADD PRIMARY KEY ({1})
            '''.format(entity_type, ','.join(pk_cols)))

        if updated_at:
            self.executeTransaction('''
                ALTER TABLE raw_{}
                ALTER COLUMN updated_at SET DEFAULT NOW()
            '''.format(entity_type))

    def create_legislative_sessions(self):
        session_ids = []

        if hasattr(settings, 'LEGISLATIVE_SESSIONS') and settings.LEGISLATIVE_SESSIONS:
            session_ids = settings.LEGISLATIVE_SESSIONS
        else:
            url = base_url + '/' + settings.OCD_JURISDICTION_ID + '/'
            r = session.get(url)
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

    def insert_raw_organizations(self, delete=False):

        self.setup_raw('organization', delete=delete)

        inserts = []

        insert_query = '''
            INSERT INTO raw_organization (
                ocd_id,
                name,
                classification,
                source_url,
                slug,
                parent_id
            ) VALUES (
                :ocd_id,
                :name,
                :classification,
                :source_url,
                :slug,
                :parent_id
            )
            '''

        for organization_json in os.listdir(self.organizations_folder):

            with open(os.path.join(self.organizations_folder, organization_json)) as f:
                org_info = json.loads(f.read())

            source_url = None
            if org_info['sources']:
                source_url = org_info['sources'][0]['url']

            parent_ocd_id = None
            if org_info['parent']:
                parent_ocd_id = org_info['parent']['id']

            ocd_part = org_info['id'].rsplit('-', 1)[1]
            slug = '{0}-{1}'.format(slugify(org_info['name']),ocd_part)

            insert = {
                'ocd_id': org_info['id'],
                'name': org_info['name'],
                'classification': org_info['classification'],
                'source_url': source_url,
                'slug': slug,
                'parent_id': parent_ocd_id,
            }

            inserts.append(insert)

        if inserts:
            self.executeTransaction(sa.text(insert_query), *inserts)

        raw_count = self.connection.execute('select count(*) from raw_organization').first().count

        self.log_message('Inserted {0} raw organizations'.format(raw_count), style='SUCCESS')

    def insert_raw_posts(self, delete=False):

        self.setup_raw('post', delete=delete)

        inserts = []

        insert_query = '''
            INSERT INTO raw_post (
                ocd_id,
                label,
                role,
                organization_id,
                division_ocd_id
            ) VALUES (
                :ocd_id,
                :label,
                :role,
                :organization_id,
                :division_ocd_id
            )
        '''

        for post_json in os.listdir(self.posts_folder):

            with open(os.path.join(self.posts_folder, post_json)) as f:
                post_info = json.loads(f.read())

            insert = {
                'ocd_id': post_info['id'],
                'label': post_info['label'],
                'role': post_info['role'],
                'organization_id': post_info['org_ocd_id'],
                'division_ocd_id': post_info['division_id'],
            }

            inserts.append(insert)

        if inserts:
            self.executeTransaction(sa.text(insert_query), *inserts)

        raw_count = self.connection.execute('select count(*) from raw_post').first().count

        self.log_message('Inserted {0} raw posts'.format(raw_count), style='SUCCESS')

    def insert_raw_people(self, delete=False):

        self.setup_raw('person', delete=delete)

        inserts = []

        insert_query = '''
            INSERT INTO raw_person (
                ocd_id,
                name,
                headshot,
                source_url,
                source_note,
                website_url,
                email,
                slug
            ) VALUES (
                :ocd_id,
                :name,
                :headshot,
                :source_url,
                :source_note,
                :website_url,
                :email,
                :slug
            )
        '''

        for person_json in os.listdir(self.people_folder):

            with open(os.path.join(self.people_folder, person_json)) as f:
                person_info = json.loads(f.read())

            source_url = None
            if person_info['sources']:
                source_url = person_info['sources'][0]['url']

            source_note = None
            if person_info['sources']:
                source_note = person_info['sources'][0]['note']

            ocd_part = person_info['id'].rsplit('-', 1)[1]
            slug = '{0}-{1}'.format(slugify(person_info['name']),ocd_part)

            insert = {
                'ocd_id': person_info['id'],
                'name': person_info['name'],
                'headshot': person_info['image'],
                'source_url': source_url,
                'source_note': source_note,
                'website_url': person_info['website_url'],
                'email': person_info['email'],
                'slug': slug,
            }

            inserts.append(insert)

        if inserts:
            self.executeTransaction(sa.text(insert_query), *inserts)

        raw_count = self.connection.execute('select count(*) from raw_person').first().count

        self.log_message('Inserted {0} raw people\n'.format(raw_count), style='SUCCESS')

    def insert_raw_memberships(self, delete=False):

        self.setup_raw('membership', delete=delete, pk_cols=[])


        inserts = []

        insert_query = '''
            INSERT INTO raw_membership (
                label,
                role,
                start_date,
                end_date,
                organization_id,
                person_id,
                post_id
            ) VALUES (
                :label,
                :role,
                :start_date,
                :end_date,
                :organization_id,
                :person_id,
                :post_id
            )
        '''

        for person_json in os.listdir(self.people_folder):

            with open(os.path.join(self.people_folder, person_json)) as f:
                person_info = json.loads(f.read())

            for membership_json in person_info['memberships']:

                end_date = parse_date(membership_json['end_date'])

                start_date = parse_date(membership_json['start_date'])

                post_id = None
                if membership_json['post']:
                    post_id = membership_json['post']['id']

                insert = {
                    'label': membership_json['label'],
                    'role': membership_json['role'],
                    'start_date': start_date,
                    'end_date': end_date,
                    'organization_id': membership_json['organization']['id'],
                    'person_id': person_info['id'],
                    'post_id': post_id,
                }

                inserts.append(insert)

        if inserts:
            self.executeTransaction(sa.text(insert_query), *inserts)

        raw_count = self.connection.execute('select count(*) from raw_membership').first().count

        self.log_message('Inserted {0} raw memberships\n'.format(raw_count), style='SUCCESS')

    def insert_raw_bills(self, delete=False):

        self.setup_raw('bill', delete=delete)

        inserts = []

        insert_query = '''
            INSERT INTO raw_bill (
                ocd_id,
                ocd_created_at,
                ocd_updated_at,
                description,
                identifier,
                classification,
                source_url,
                source_note,
                from_organization_id,
                full_text,
                ocr_full_text,
                abstract,
                legislative_session_id,
                bill_type,
                subject,
                slug
            ) VALUES (
                :ocd_id,
                :ocd_created_at,
                :ocd_updated_at,
                :description,
                :identifier,
                :classification,
                :source_url,
                :source_note,
                :from_organization_id,
                :full_text,
                :ocr_full_text,
                :abstract,
                :legislative_session_id,
                :bill_type,
                :subject,
                :slug
            )
            '''

        counter = 0

        for bill_json in os.listdir(self.bills_folder):

            with open(os.path.join(self.bills_folder, bill_json)) as f:
                bill_info = json.loads(f.read())

            source_url = None
            for source in bill_info['sources']:
                if source['note'] == 'web':
                    source_url = source['url']

            full_text = None
            if 'full_text' in bill_info['extras']:
                full_text = bill_info['extras']['full_text']

            ocr_full_text = None
            if 'ocr_full_text' in bill_info['extras']:
                ocr_full_text = bill_info['extras']['ocr_full_text']

            elif 'plain_text' in bill_info['extras']:
                ocr_full_text = bill_info['extras']['plain_text']

            abstract = None
            if bill_info['abstracts']:
                abstract = bill_info['abstracts'][0]['abstract']

            if bill_info['extras'].get('local_classification'):
                bill_type = bill_info['extras']['local_classification']

            elif len(bill_info['classification']) == 1:
                bill_type = bill_info['classification'][0]

            else:
                raise Exception(bill_info['classification'])

            subject = None
            if 'subject' in bill_info and bill_info['subject']:
                subject = bill_info['subject'][0]

            slug = slugify(bill_info['identifier'])

            insert = {
                'ocd_id': bill_info['id'],
                'ocd_created_at': bill_info['created_at'],
                'ocd_updated_at': bill_info['updated_at'],
                'description': bill_info['title'],
                'identifier': bill_info['identifier'],
                'classification': bill_info['classification'][0],
                'source_url': source_url,
                'source_note': bill_info['sources'][0]['note'],
                'from_organization_id': bill_info['from_organization']['id'],
                'full_text': full_text,
                'ocr_full_text': ocr_full_text,
                'abstract': abstract,
                'legislative_session_id': bill_info['legislative_session']['identifier'],
                'bill_type': bill_type,
                'subject': subject,
                'slug': slug,
            }

            inserts.append(insert)

            if inserts and len(inserts) % 10000 == 0:
                self.executeTransaction(sa.text(insert_query), *inserts)

                counter += 10000
                self.log_message('Inserted {} raw bills'.format(counter))

                inserts = []

        if inserts:

            self.executeTransaction(sa.text(insert_query), *inserts)

            counter += len(inserts)

        self.log_message('Inserted a total of {} raw bills\n'.format(counter), style='SUCCESS')

    def insert_raw_actions(self, delete=False):

        pk_cols = ['bill_id', '"order"']

        self.setup_raw('action', delete=delete, pk_cols=pk_cols)

        inserts = []

        insert_query = '''
            INSERT INTO raw_action (
                date,
                classification,
                description,
                organization_id,
                bill_id,
                "order"
            ) VALUES (
                :date,
                :classification,
                :description,
                :organization_id,
                :bill_id,
                :order
            )
            '''

        counter = 0
        for bill_json in os.listdir(self.bills_folder):

            with open(os.path.join(self.bills_folder, bill_json)) as f:
                bill_info = json.loads(f.read())

            for order, action in enumerate(bill_info['actions']):

                classification = None
                if action['classification']:
                    classification = action['classification'][0]

                action_date = app_timezone.localize(date_parser.parse(action['date']))

                insert = {
                    'date': action_date,
                    'classification': classification,
                    'description': action['description'],
                    'organization_id': action['organization']['id'],
                    'bill_id': bill_info['id'],
                    'order': order
                }

                inserts.append(insert)

                if inserts and len(inserts) % 10000 == 0:
                    self.executeTransaction(sa.text(insert_query), *inserts)

                    counter += 10000

                    self.log_message('Inserted {0} actions'.format(counter))

                    inserts = []

        if inserts:
            self.executeTransaction(sa.text(insert_query), *inserts)

            counter += len(inserts)

        self.log_message('Inserted {0} actions\n'.format(counter), style='SUCCESS')


    def insert_raw_action_related_entity(self, delete=False):

        self.remake_raw('actionrelatedentity', delete=delete)

        self.executeTransaction('''
            ALTER TABLE raw_actionrelatedentity
            ALTER COLUMN updated_at SET DEFAULT NOW()
        ''')

        inserts = []

        insert_query = '''
            INSERT INTO raw_actionrelatedentity (
                entity_type,
                entity_name,
                organization_ocd_id,
                person_ocd_id,
                action_id
            ) VALUES (
                :entity_type,
                :entity_name,
                :organization_ocd_id,
                :person_ocd_id,
                :action_id
            )
            '''

        counter = 0
        for bill_json in os.listdir(self.bills_folder):
            with open(os.path.join(self.bills_folder, bill_json)) as f:
                bill_info = json.load(f)

            db_actions = self.connection.execute(sa.text("""
                                SELECT id
                                FROM councilmatic_core_action
                                WHERE bill_id = :bill_id
                                ORDER by "order"
                                """), bill_id=bill_info["id"])

            actions = list(zip((action.id for action in db_actions),
                               bill_info['actions']))

            for action_id, action in actions:

                for related_entity in action['related_entities']:

                    person_id = None
                    organization_id = None

                    if related_entity['entity_type'] == 'organization':

                        organization_id = related_entity['organization_id']

                        if not organization_id:
                            org_id = self.connection.execute(sa.text("""
                                SELECT ocd_id
                                FROM councilmatic_core_organization
                                WHERE name = :name
                                LIMIT 1
                            """), name=related_entity['name']).first()

                            if org_id:
                                organization_id = org_id.ocd_id

                    elif related_entity['entity_type'] == 'person':

                        person_id = related_entity['person_id']

                        if not person_id:
                            person_id = self.connection.execute(sa.text("""
                                SELECT ocd_id
                                FROM councilmatic_core_person
                                WHERE name = :name
                                LIMIT 1
                            """), name=related_entity['name']).first()

                            if person_id:
                                person_id = person_id.ocd_id

                    insert = {
                        'entity_type': related_entity['entity_type'],
                        'entity_name': related_entity['name'],
                        'organization_ocd_id': organization_id,
                        'person_ocd_id': person_id,
                        'action_id': action_id,
                    }

                    inserts.append(insert)

                    if inserts and len(inserts) % 10000 == 0:
                        self.executeTransaction(sa.text(insert_query), *inserts)

                        counter += 10000
                        self.log_message('Inserted {0} action related entities'.format(counter))

                        inserts = []

        if inserts:
            self.executeTransaction(sa.text(insert_query), *inserts)

            counter += len(inserts)

        self.log_message('Inserted {0} action related entities\n'.format(counter), style='SUCCESS')


    def insert_raw_sponsorships(self, delete=False):

        self.remake_raw('sponsorship', delete=delete)

        self.executeTransaction('''
                ALTER TABLE raw_sponsorship
                ALTER COLUMN updated_at SET DEFAULT NOW()
            ''')

        self.executeTransaction('''
                DROP TABLE IF EXISTS raw_sponsorship_temp
            ''')

        self.executeTransaction('''
                CREATE TABLE raw_sponsorship_temp AS (
                    SELECT * FROM councilmatic_core_sponsorship
                ) WITH NO DATA
            ''')

        self.executeTransaction('''
                ALTER TABLE raw_sponsorship_temp
                ALTER COLUMN updated_at SET DEFAULT NOW()
            ''')

        inserts = []

        insert_query = '''
            INSERT INTO raw_sponsorship_temp (
                classification,
                is_primary,
                bill_id,
                person_id
            ) VALUES (
                :classification,
                :is_primary,
                :bill_id,
                :person_id
            )
            '''

        counter = 0
        for bill_json in os.listdir(self.bills_folder):

            with open(os.path.join(self.bills_folder, bill_json)) as f:
                bill_info = json.loads(f.read())

            for sponsorship in bill_info['sponsorships']:

                # TODO: Sponsorships can also be organizations but we're
                # waiting to see what that actually means

                if sponsorship['entity_type'] == 'person':

                    insert = {
                        'classification': sponsorship['classification'],
                        'is_primary': sponsorship['primary'],
                        'bill_id': bill_info['id'],
                        'person_id': sponsorship['entity_id'],
                    }

                    inserts.append(insert)

                if inserts and len(inserts) % 10000 == 0:
                    self.executeTransaction(sa.text(insert_query), *inserts)

                    counter += 10000
                    self.log_message('Inserted {0} raw sponsorships'.format(counter))

                    inserts = []

        if inserts:
            self.executeTransaction(sa.text(insert_query), *inserts)

        # Temproary measure to make sure we can actually update things.
        self.executeTransaction('''
                INSERT INTO raw_sponsorship
                  SELECT DISTINCT ON (classification, is_primary, bill_id, person_id)
                  *
                  FROM raw_sponsorship_temp
            ''')

        raw_count = self.connection.execute('select count(*) from raw_sponsorship').first().count
        self.log_message('Inserted {0} raw sponsorships\n'.format(raw_count), style='SUCCESS')

    def insert_raw_billdocuments(self, delete=False):

        self.remake_raw('billdocument', delete=delete)

        self.executeTransaction('''
                ALTER TABLE raw_billdocument
                ALTER COLUMN updated_at SET DEFAULT NOW()
            ''')

        inserts = []

        insert_query = '''
            INSERT INTO raw_billdocument (
                note,
                url,
                bill_id,
                document_type
            ) VALUES (
                :note,
                :url,
                :bill_id,
                :document_type
            )
        '''

        counter = 0
        for bill_json in os.listdir(self.bills_folder):

            with open(os.path.join(self.bills_folder, bill_json)) as f:
                bill_info = json.loads(f.read())

            for document in bill_info['documents']:

                insert = {
                    'note': document['note'],
                    'url': document['links'][0]['url'],
                    'bill_id': bill_info['id'],
                    'document_type': 'A',
                }

                inserts.append(insert)

            for document in bill_info['versions']:

                insert = {
                    'note': document['note'],
                    'url': document['links'][0]['url'],
                    'bill_id': bill_info['id'],
                    'document_type': 'V',
                }

                inserts.append(insert)

            if inserts and len(inserts) % 10000 == 0:
                self.executeTransaction(sa.text(insert_query), *inserts)

                counter += 10000

                self.log_message('Inserted {0} raw bill attachments and versions'.format(counter))

                inserts = []

        if inserts:
            self.executeTransaction(sa.text(insert_query), *inserts)

            counter += len(inserts)

        self.log_message('Inserted {0} raw bill attachments and versions\n'.format(counter), style='SUCCESS')


    def insert_raw_events(self, delete=False):
        self.setup_raw('event', delete=delete)

        inserts = []

        insert_query = '''
            INSERT INTO raw_event (
                ocd_id,
                ocd_created_at,
                ocd_updated_at,
                name,
                description,
                classification,
                start_time,
                end_time,
                all_day,
                status,
                location_name,
                location_url,
                media_url,
                source_url,
                source_note,
                slug
            ) VALUES (
                :ocd_id,
                :ocd_created_at,
                :ocd_updated_at,
                :name,
                :description,
                :classification,
                :start_time,
                :end_time,
                :all_day,
                :status,
                :location_name,
                :location_url,
                :media_url,
                :source_url,
                :source_note,
                :slug
            )
        '''

        counter = 0

        for event_json in os.listdir(self.events_folder):

            with open(os.path.join(self.events_folder, event_json)) as f:
                event_info = json.loads(f.read())

            ocd_id = event_info['id']

            truncator = Truncator(event_info['name'])
            ocd_part = ocd_id.rsplit('-', 1)[1]
            slug = '{0}-{1}'.format(slugify(truncator.words(5)), ocd_part)

            for el in event_info['sources']:
                if el['note'] == 'web':
                    source_url = el['url']
                    break
                else:
                    source_url = el['url']

            insert = {
                'ocd_id': ocd_id,
                'ocd_created_at': event_info['created_at'],
                'ocd_updated_at': event_info['updated_at'],
                'name': event_info['name'],
                'description': event_info['description'],
                'classification': event_info['classification'],
                'start_time': parse_datetime(event_info['start_date']),
                'end_time': parse_datetime(event_info['end_date']) if event_info['end_date'] else None,
                'all_day': event_info['all_day'],
                'status': event_info['status'],
                'location_name': event_info['location']['name'],
                'location_url': event_info['location']['url'],
                'media_url': event_info['media'][0]['links'][0]['url'] if event_info['media'] else None,
                'source_url': source_url,
                'source_note': event_info['sources'][0]['note'],
                'slug': slug,
            }

            inserts.append(insert)

            if inserts and len(inserts) % 10000 == 0:
                self.executeTransaction(sa.text(insert_query), *inserts)

                counter += 10000

                self.log_message('Inserted {0} raw events'.format(counter))

                inserts = []

        if inserts:
            self.executeTransaction(sa.text(insert_query), *inserts)

            counter += len(inserts)

        self.log_message('Inserted {0} raw events\n'.format(counter), style='SUCCESS')

    def insert_raw_eventparticipants(self, delete=False):
        pk_cols = ['event_id', 'entity_name', 'entity_type']

        self.setup_raw('eventparticipant',
                       delete=delete,
                       pk_cols=pk_cols)

        inserts = []

        insert_query = '''
            INSERT INTO raw_eventparticipant (
                note,
                entity_name,
                entity_type,
                event_id
            ) VALUES (
                :note,
                :entity_name,
                :entity_type,
                :event_id
            )
            '''

        counter = 0
        for event_json in os.listdir(self.events_folder):

            with open(os.path.join(self.events_folder, event_json)) as f:
                event_info = json.loads(f.read())

            for participant in event_info['participants']:

                insert = {
                    'note': participant['note'],
                    'entity_name': participant['entity_name'],
                    'entity_type': participant['entity_type'],
                    'event_id': event_info['id'],
                }

                inserts.append(insert)

                if inserts and len(inserts) % 10000 == 0:
                    self.executeTransaction(sa.text(insert_query), *inserts)

                    counter += 10000

                    self.log_message('Inserted {} raw event participants'.format(counter))

                    inserts = []

        if inserts:
            self.executeTransaction(sa.text(insert_query), *inserts)
            counter += len(inserts)

        self.log_message('Inserted {0} event participants\n'.format(counter), style='SUCCESS')

    def insert_raw_eventdocuments(self, delete=False):
        pk_cols = ['event_id', 'url']

        self.setup_raw('eventdocument',
                       delete=delete,
                       pk_cols=pk_cols,
                       updated_at=False)

        inserts = []

        insert_query = '''
            INSERT INTO raw_eventdocument (
                event_id,
                note,
                url
            ) VALUES (
                :event_id,
                :note,
                :url
            )
            '''

        counter = 0
        for event_json in os.listdir(self.events_folder):

            with open(os.path.join(self.events_folder, event_json)) as f:
                event_info = json.loads(f.read())

            for document in event_info['documents']:

                insert = {
                    'event_id': event_info['id'],
                    'note': document['note'],
                    'url': document['links'][0]['url'],
                }

                inserts.append(insert)

                if inserts and len(inserts) % 10000 == 0:
                    self.executeTransaction(sa.text(insert_query), *inserts)

                    counter += 10000

                    self.log_message('Inserted {} raw event documents'.format(counter))

                    inserts = []

        if inserts:
            self.executeTransaction(sa.text(insert_query), *inserts)

            counter += len(inserts)

        self.log_message('Inserted {0} event documents\n'.format(counter), style='SUCCESS')

    def insert_raw_event_agenda_items(self, delete=False):
        pk_cols = ['event_id', '"order"']

        self.setup_raw('eventagendaitem',
                       delete=delete,
                       pk_cols=pk_cols)

        inserts = []

        insert_query = '''
            INSERT INTO raw_eventagendaitem (
                "order",
                description,
                event_id,
                bill_id,
                note,
                notes
            ) VALUES (
                :order,
                :description,
                :event_id,
                :bill_id,
                :note,
                :notes
            )
            '''

        counter = 0

        for event_json in os.listdir(self.events_folder):

            with open(os.path.join(self.events_folder, event_json)) as f:
                event_info = json.loads(f.read())

            for item in event_info['agenda']:

                bill_id = None
                note = None

                try:
                    related_entity = item['related_entities'][0]

                    # Only capture related entities when they are bills
                    if related_entity['entity_type'] == 'bill':
                        bill_id = related_entity['entity_id']
                        note = related_entity['note']

                except IndexError:
                    pass

                notes = ''
                if item['notes']:
                    notes = item['notes'][0]

                insert = {
                    'order': item['order'],
                    'description': item['description'],
                    'event_id': event_info['id'],
                    'bill_id': bill_id,
                    'note': note,
                    'notes': notes,
                }

                inserts.append(insert)
                if inserts and len(inserts) % 10000 == 0:
                    self.executeTransaction(sa.text(insert_query), *inserts)

                    counter += 10000

                    self.log_message('Inserted {} raw event agenda items'.format(counter))

                    inserts = []

        if inserts:
            self.executeTransaction(sa.text(insert_query), *inserts)

            counter += len(inserts)

        self.log_message('Inserted {0} raw event agenda items\n'.format(counter), style='SUCCESS')

    ################################
    ###                          ###
    ### UPDATE EXISTING ENTITIES ###
    ###                          ###
    ################################

    def setup_update(self, entity_type):
        self.executeTransaction('DROP TABLE IF EXISTS change_{}'.format(entity_type))

        self.executeTransaction('''
            CREATE TABLE change_{} (
                ocd_id VARCHAR,
                PRIMARY KEY (ocd_id)
            )
        '''.format(entity_type))

    def get_update_parts(self, cols, extra_cols):
        wheres = []
        sets = []
        fields = []
        for col in cols:
            condition = '''
                ((raw."{0}" IS NOT NULL OR dat."{0}" IS NOT NULL) AND
                COALESCE(raw."{0}"::VARCHAR, '') <> COALESCE(dat."{0}"::VARCHAR, ''))
            '''.format(col)
            wheres.append(condition)

            sets.append('"{0}"=s."{0}"'.format(col))
            fields.append('raw."{0}"'.format(col))

        for col in extra_cols:
            sets.append('"{0}"=s."{0}"'.format(col))
            fields.append('raw."{0}"'.format(col))

        where_clause = ' OR '.join(wheres)
        set_values = ', '.join(sets)
        fields = ', '.join(fields)

        return where_clause, set_values, fields

    def update_entity_type(self, entity_type, cols=[], extra_cols=['updated_at']):

        self.setup_update(entity_type)

        where_clause, set_values, fields = self.get_update_parts(cols, extra_cols)

        find_changes = '''
            INSERT INTO change_{0}
              SELECT raw.ocd_id
              FROM raw_{0} AS raw
              JOIN councilmatic_core_{0} AS dat
                ON raw.ocd_id = dat.ocd_id
              WHERE {1}
        '''.format(entity_type, where_clause)

        update_dat = '''
            UPDATE councilmatic_core_{entity_type} SET
              {set_values}
            FROM (
              SELECT
                {fields}
              FROM raw_{entity_type} AS raw
              JOIN change_{entity_type} AS change
                ON raw.ocd_id = change.ocd_id
            ) AS s
            WHERE councilmatic_core_{entity_type}.ocd_id = s.ocd_id
        '''.format(set_values=set_values,
                   fields=fields,
                   entity_type=entity_type)

        self.executeTransaction(find_changes)
        self.executeTransaction(update_dat)

        change_count = self.connection.execute('select count(*) from change_{}'.format(entity_type)).first().count

        self.log_message('Found {0} changed {1}'.format(change_count, entity_type), style='SUCCESS')

    def update_existing_organizations(self):

        cols = [
            'ocd_id',
            'name',
            'classification',
            'source_url',
            'parent_id',
            'slug'
        ]

        self.update_entity_type('organization', cols=cols)

    def update_existing_posts(self):

        cols = [
            'ocd_id',
            'label',
            'role',
            'organization_id',
            'division_ocd_id'
        ]

        self.update_entity_type('post', cols=cols)

    def update_existing_people(self):
        cols = [
            'ocd_id',
            'name',
            'headshot',
            'source_url',
            'source_note',
            'website_url',
            'email',
            'slug',
        ]
        self.update_entity_type('person', cols=cols)

    def update_existing_memberships(self):

        self.executeTransaction('DROP TABLE IF EXISTS change_membership')
        self.executeTransaction('''
            CREATE TABLE change_membership (
                organization_id VARCHAR,
                person_id VARCHAR,
                post_id VARCHAR,
                start_date DATE,
                end_date DATE
            )
        ''')

        cols = [
           'label',
           'role',
           'start_date',
           'end_date',
           'organization_id',
           'person_id',
           'post_id'
        ]

        where_clause, set_values, fields = self.get_update_parts(cols, [])

        find_changes = '''
            INSERT INTO change_membership
              SELECT
                raw.organization_id,
                raw.person_id,
                raw.post_id,
                raw.start_date,
                raw.end_date
              FROM raw_membership AS raw
              JOIN councilmatic_core_membership AS dat
                ON (raw.organization_id = dat.organization_id
                    AND raw.person_id = dat.person_id
                    AND COALESCE(raw.post_id, '') = COALESCE(dat.post_id, '')
                    AND COALESCE(raw.start_date, '1900-01-01') = COALESCE(dat.start_date, '1900-01-01')
                    AND COALESCE(raw.end_date, NOW()) = COALESCE(dat.end_date, NOW()))
              WHERE {}
        '''.format(where_clause)

        update_dat = '''
            UPDATE councilmatic_core_membership SET
              {set_values}
            FROM (
              SELECT
                {fields}
              FROM raw_membership AS raw
              JOIN change_membership AS change
                ON (raw.organization_id = change.organization_id
                    AND raw.person_id = change.person_id
                    AND COALESCE(raw.post_id, '') = COALESCE(change.post_id, '')
                    AND COALESCE(raw.start_date, '1900-01-01') = COALESCE(change.start_date, '1900-01-01')
                    AND COALESCE(raw.end_date, NOW()) = COALESCE(change.end_date, NOW()))
            ) AS s
            WHERE councilmatic_core_membership.organization_id = s.organization_id
              AND councilmatic_core_membership.person_id = s.person_id
              AND COALESCE(councilmatic_core_membership.post_id, '') = COALESCE(s.post_id, '')
              AND COALESCE(councilmatic_core_membership.start_date, '1900-01-01') = COALESCE(s.start_date, '1900-01-01')
              AND COALESCE(councilmatic_core_membership.end_date, NOW()) = COALESCE(s.end_date, NOW())
        '''.format(set_values=set_values,
                   fields=fields)

        self.executeTransaction(find_changes)
        self.executeTransaction(update_dat)

        change_count = self.connection.execute('select count(*) from change_membership').first().count

        self.log_message('Found {0} changed membership'.format(change_count), style='SUCCESS')

    def update_existing_bills(self):
        cols = [
            'ocd_id',
            'ocd_created_at',
            'ocd_updated_at',
            'description',
            'identifier',
            'bill_type',
            'classification',
            'source_url',
            'source_note',
            'subject',
            'from_organization_id',
            'full_text',
            'ocr_full_text',
            'abstract',
            'last_action_date',
            'legislative_session_id',
            'slug',
        ]
        self.update_entity_type('bill', cols=cols)

    def update_existing_actions(self):

        self.executeTransaction('DROP TABLE IF EXISTS change_action')
        self.executeTransaction('''
            CREATE TABLE change_action (
                bill_id VARCHAR,
                "order" INTEGER
            )
        ''')

        cols = [
            'date',
            'classification',
            'description',
            'order',
            'bill_id',
            'organization_id',
        ]

        where_clause, set_values, fields = self.get_update_parts(cols, ['updated_at'])

        find_changes = '''
            INSERT INTO change_action
              SELECT
                raw.bill_id,
                raw."order"
              FROM raw_action AS raw
              JOIN councilmatic_core_action AS dat
                ON (raw.bill_id = dat.bill_id
                    AND raw."order" = dat."order")
              WHERE {}
        '''.format(where_clause)

        update_dat = '''
            UPDATE councilmatic_core_action SET
              {set_values}
            FROM (
              SELECT
                {fields}
              FROM raw_action AS raw
              JOIN change_action AS change
                ON (raw.bill_id = change.bill_id
                    AND raw."order" = change."order")
            ) AS s
            WHERE councilmatic_core_action.bill_id = s.bill_id
              AND councilmatic_core_action."order" = s."order"
        '''.format(set_values=set_values,
                   fields=fields)

        self.executeTransaction(find_changes)

        self.executeTransaction(update_dat)
        change_count = self.connection.execute('select count(*) from change_action').first().count

        self.log_message('Found {0} changed action'.format(change_count), style='SUCCESS')

    def update_existing_action_related_entity(self):
        self.executeTransaction('DROP TABLE IF EXISTS change_actionrelatedentity')
        self.executeTransaction('''
            CREATE TABLE change_actionrelatedentity (
                organization_ocd_id VARCHAR,
                person_ocd_id VARCHAR,
                action_id INTEGER
            )
        ''')

        cols = [
            'entity_type',
            'entity_name',
            'organization_ocd_id',
            'person_ocd_id',
            'action_id',
        ]

        where_clause, set_values, fields = self.get_update_parts(cols, ['updated_at'])

        find_changes = '''
            INSERT INTO change_actionrelatedentity
              SELECT
                raw.organization_ocd_id,
                raw.person_ocd_id,
                raw.action_id
              FROM raw_actionrelatedentity AS raw
              JOIN councilmatic_core_actionrelatedentity AS dat
                ON (COALESCE(raw.organization_ocd_id, '') = COALESCE(dat.organization_ocd_id, '')
                    AND COALESCE(raw.person_ocd_id, '') = COALESCE(dat.person_ocd_id, '')
                    AND raw.action_id = dat.action_id)
              WHERE {}
        '''.format(where_clause)

        update_dat = '''
            UPDATE councilmatic_core_actionrelatedentity SET
              {set_values}
            FROM (
              SELECT
                {fields}
              FROM raw_actionrelatedentity AS raw
              JOIN change_actionrelatedentity AS change
                ON (COALESCE(raw.organization_ocd_id, '') = COALESCE(change.organization_ocd_id, '')
                    AND COALESCE(raw.person_ocd_id, '') = COALESCE(change.person_ocd_id, '')
                    AND raw.action_id = change.action_id)
            ) AS s
            WHERE COALESCE(councilmatic_core_actionrelatedentity.organization_ocd_id, '') = COALESCE(s.organization_ocd_id, '')
              AND COALESCE(councilmatic_core_actionrelatedentity.person_ocd_id, '') = COALESCE(s.person_ocd_id, '')
              AND councilmatic_core_actionrelatedentity.action_id = s.action_id
        '''.format(set_values=set_values,
                   fields=fields)

        self.executeTransaction(find_changes)
        self.executeTransaction(update_dat)

        change_count = self.connection.execute('select count(*) from change_actionrelatedentity').first().count

        self.log_message('Found {0} changed action related entities'.format(change_count), style='SUCCESS')

    def update_existing_sponsorships(self):
        self.executeTransaction('DROP TABLE IF EXISTS change_sponsorship')
        self.executeTransaction('''
            CREATE TABLE change_sponsorship (
                classification VARCHAR,
                is_primary BOOLEAN,
                bill_id VARCHAR,
                person_id VARCHAR
            )
        ''')

        cols = [
            'classification',
            'is_primary',
            'bill_id',
            'person_id',
        ]

        where_clause, set_values, fields = self.get_update_parts(cols, ['updated_at'])

        find_changes = '''
            INSERT INTO change_sponsorship
              SELECT
                raw.classification,
                raw.is_primary,
                raw.bill_id,
                raw.person_id
              FROM raw_sponsorship AS raw
              JOIN councilmatic_core_sponsorship AS dat
                ON (raw.classification = dat.classification
                    AND raw.is_primary = dat.is_primary
                    AND raw.bill_id = dat.bill_id
                    AND raw.person_id = dat.person_id)
              WHERE {}
        '''.format(where_clause)

        update_dat = '''
            UPDATE councilmatic_core_sponsorship SET
              {set_values}
            FROM (
              SELECT
                {fields}
              FROM raw_sponsorship AS raw
              JOIN change_sponsorship AS change
                ON (raw.classification = change.classification
                    AND raw.is_primary = change.is_primary
                    AND raw.bill_id = change.bill_id
                    AND raw.person_id = change.person_id)
            ) AS s
            WHERE councilmatic_core_sponsorship.classification = s.classification
              AND councilmatic_core_sponsorship.is_primary = s.is_primary
              AND councilmatic_core_sponsorship.bill_id = s.bill_id
              AND councilmatic_core_sponsorship.person_id = s.person_id
        '''.format(set_values=set_values,
                   fields=fields)

        self.executeTransaction(find_changes)

        self.executeTransaction(update_dat)

        change_count = self.connection.execute('select count(*) from change_sponsorship').first().count

        self.log_message('Found {0} changed sponsorships'.format(change_count), style='SUCCESS')

    def update_existing_billdocuments(self):
        self.executeTransaction('DROP TABLE IF EXISTS change_billdocument')
        self.executeTransaction('''
            CREATE TABLE change_billdocument (
                bill_id VARCHAR,
                url VARCHAR,
                document_type VARCHAR
            )
        ''')

        cols = [
            'bill_id',
            'url',
            'document_type',
            'note',
        ]

        where_clause, set_values, fields = self.get_update_parts(cols, ['updated_at'])

        find_changes = '''
            INSERT INTO change_billdocument
              SELECT
                raw.bill_id,
                raw.url,
                raw.document_type
              FROM raw_billdocument AS raw
              JOIN councilmatic_core_billdocument AS dat
                ON (raw.bill_id = dat.bill_id
                    AND raw.url = dat.url
                    AND raw.document_type = dat.document_type)
              WHERE {}
        '''.format(where_clause)

        update_dat = '''
            UPDATE councilmatic_core_billdocument SET
              {set_values}
            FROM (
              SELECT
                {fields}
              FROM raw_billdocument AS raw
              JOIN change_billdocument AS change
                ON (raw.bill_id = change.bill_id
                    AND raw.url = change.url
                    AND raw.document_type = change.document_type)
            ) AS s
            WHERE councilmatic_core_billdocument.bill_id = s.bill_id
              AND councilmatic_core_billdocument.url = s.url
              AND councilmatic_core_billdocument.document_type = s.document_type
        '''.format(set_values=set_values,
                   fields=fields)

        self.executeTransaction(find_changes)

        self.executeTransaction(update_dat)

        change_count = self.connection.execute('select count(*) from change_billdocument').first().count

        self.log_message('Found {0} changed bill documents'.format(change_count), style='SUCCESS')

    def update_existing_events(self):
        cols = [
            'ocd_id',
            'ocd_created_at',
            'ocd_updated_at',
            'name',
            'description',
            'classification',
            'start_time',
            'end_time',
            'all_day',
            'status',
            'location_name',
            'location_url',
            'media_url',
            'source_url',
            'source_note',
            'slug',
        ]
        self.update_entity_type('event', cols=cols)

    def update_existing_eventparticipants(self):
        self.executeTransaction('DROP TABLE IF EXISTS change_eventparticipant')
        self.executeTransaction('''
            CREATE TABLE change_eventparticipant (
                event_id VARCHAR,
                entity_name VARCHAR,
                entity_type VARCHAR
            )
        ''')

        cols = [
            'event_id',
            'entity_type',
            'entity_name',
            'note',
        ]

        where_clause, set_values, fields = self.get_update_parts(cols, ['updated_at'])

        find_changes = '''
            INSERT INTO change_eventparticipant
              SELECT
                raw.event_id,
                raw.entity_type,
                raw.entity_name
              FROM raw_eventparticipant AS raw
              JOIN councilmatic_core_eventparticipant AS dat
                ON (raw.event_id = dat.event_id
                    AND raw.entity_type = dat.entity_type
                    AND raw.entity_name = dat.entity_name)
              WHERE {}
        '''.format(where_clause)

        update_dat = '''
            UPDATE councilmatic_core_eventparticipant SET
              {set_values}
            FROM (
              SELECT
                {fields}
              FROM raw_eventparticipant AS raw
              JOIN change_eventparticipant AS change
                ON (raw.event_id = change.event_id
                    AND raw.entity_type = change.entity_type
                    AND raw.entity_name = change.entity_name)
            ) AS s
            WHERE councilmatic_core_eventparticipant.event_id = s.event_id
              AND councilmatic_core_eventparticipant.entity_type = s.entity_type
              AND councilmatic_core_eventparticipant.entity_name = s.entity_name
        '''.format(set_values=set_values,
                   fields=fields)

        self.executeTransaction(find_changes)
        self.executeTransaction(update_dat)

        change_count = self.connection.execute('select count(*) from change_eventparticipant').first().count

        self.log_message('Found {0} changed event participants'.format(change_count), style='SUCCESS')

    def update_existing_eventdocuments(self):
        self.executeTransaction('DROP TABLE IF EXISTS change_eventdocument')
        self.executeTransaction('''
            CREATE TABLE change_eventdocument (
                event_id VARCHAR,
                url VARCHAR
            )
        ''')

        cols = [
            'event_id',
            'url',
            'full_text',
            'note'
        ]

        where_clause, set_values, fields = self.get_update_parts(cols, [])

        find_changes = '''
            INSERT INTO change_eventdocument
              SELECT
                raw.event_id,
                raw.url
              FROM raw_eventdocument AS raw
              JOIN councilmatic_core_eventdocument AS dat
                ON (raw.event_id = dat.event_id
                    AND raw.url = dat.url)
              WHERE {}
        '''.format(where_clause)

        update_dat = '''
            UPDATE councilmatic_core_eventdocument SET
              {set_values}
            FROM (
              SELECT
                {fields}
              FROM raw_eventdocument AS raw
              JOIN change_eventdocument AS change
                ON (raw.event_id = change.event_id
                    AND raw.url = change.url)
            ) AS s
            WHERE councilmatic_core_eventdocument.event_id = s.event_id
              AND councilmatic_core_eventdocument.url = s.url
        '''.format(set_values=set_values,
                   fields=fields)

        self.executeTransaction(find_changes)
        self.executeTransaction(update_dat)

        change_count = self.connection.execute('select count(*) from change_eventdocument').first().count

        self.log_message('Found {0} changed event documents'.format(change_count), style='SUCCESS')

    def update_existing_event_agenda_items(self):
        self.executeTransaction('DROP TABLE IF EXISTS change_eventagendaitem')
        self.executeTransaction('''
            CREATE TABLE change_eventagendaitem (
                event_id VARCHAR,
                "order" INTEGER
            )
        ''')

        cols = [
            'order',
            'description',
            'event_id',
            'bill_id',
            'note',
            'notes',
        ]

        where_clause, set_values, fields = self.get_update_parts(cols, ['updated_at'])

        find_changes = '''
            INSERT INTO change_eventagendaitem
              SELECT
                raw.event_id,
                raw."order"
              FROM raw_eventagendaitem AS raw
              JOIN councilmatic_core_eventagendaitem AS dat
                ON (raw.event_id = dat.event_id
                    AND raw."order" = dat."order")
              WHERE {}
        '''.format(where_clause)

        update_dat = '''
            UPDATE councilmatic_core_eventagendaitem SET
              {set_values}
            FROM (
              SELECT
                {fields}
              FROM raw_eventagendaitem AS raw
              JOIN change_eventagendaitem AS change
                ON (raw.event_id = change.event_id
                    AND raw."order" = change."order")
            ) AS s
            WHERE councilmatic_core_eventagendaitem.event_id = s.event_id
              AND councilmatic_core_eventagendaitem."order" = s."order"
        '''.format(set_values=set_values,
                   fields=fields)

        self.executeTransaction(find_changes)
        self.executeTransaction(update_dat)

        change_count = self.connection.execute('select count(*) from change_eventagendaitem').first().count

        self.log_message('Found {0} changed event agenda items'.format(change_count), style='SUCCESS')

    ########################
    ###                  ###
    ### ADD NEW ENTITIES ###
    ###                  ###
    ########################

    def add_entity_type(self, entity_type, cols=[], extra_cols=['updated_at']):
        self.executeTransaction('DROP TABLE IF EXISTS new_{}'.format(entity_type))
        self.executeTransaction('''
            CREATE TABLE new_{} (
                ocd_id VARCHAR,
                PRIMARY KEY (ocd_id)
            )
        '''.format(entity_type))

        find_new = '''
            INSERT INTO new_{0}
              SELECT raw.ocd_id
              FROM raw_{0} AS raw
              LEFT JOIN councilmatic_core_{0} AS dat
                ON raw.ocd_id = dat.ocd_id
              WHERE dat.ocd_id IS NULL
        '''.format(entity_type)

        self.executeTransaction(find_new)

        cols = cols + extra_cols

        insert_fields = ', '.join(c for c in cols)
        select_fields = ', '.join('raw.{}'.format(c) for c in cols)

        insert_new = '''
            INSERT INTO councilmatic_core_{entity_type} (
              {insert_fields}
            )
              SELECT {select_fields}
              FROM raw_{entity_type} AS raw
              JOIN new_{entity_type} AS new
                USING(ocd_id)
        '''.format(entity_type=entity_type,
                   insert_fields=insert_fields,
                   select_fields=select_fields)

        self.executeTransaction(insert_new)

        new_count = self.connection.execute('select count(*) from new_{}'.format(entity_type)).first().count

        self.log_message('Found {0} new {1}'.format(new_count, entity_type), style='SUCCESS')

    def add_new_organizations(self):
        cols = [
            'ocd_id',
            'name',
            'classification',
            'source_url',
            'parent_id',
            'slug',
        ]

        self.add_entity_type('organization', cols=cols)

    def add_new_posts(self):
        cols = [
            'ocd_id',
            'label',
            'role',
            'organization_id',
            'division_ocd_id'
        ]

        self.add_entity_type('post', cols=cols)

    def add_new_people(self):
        cols = [
            'ocd_id',
            'name',
            'headshot',
            'source_url',
            'source_note',
            'website_url',
            'email',
            'slug',
        ]

        self.add_entity_type('person', cols=cols)

    def add_new_memberships(self):
        self.executeTransaction('DROP TABLE IF EXISTS new_membership')
        self.executeTransaction('''
            CREATE TABLE new_membership (
                organization_id VARCHAR,
                person_id VARCHAR,
                post_id VARCHAR,
                start_date DATE,
                end_date DATE
            )
        ''')

        find_new = '''
            INSERT INTO new_membership
              SELECT
                raw.organization_id,
                raw.person_id,
                raw.post_id,
                raw.start_date,
                raw.end_date
              FROM raw_membership AS raw
              LEFT JOIN councilmatic_core_membership AS dat
                ON (raw.organization_id = dat.organization_id
                    AND raw.person_id = dat.person_id
                    AND COALESCE(raw.post_id, '') = COALESCE(dat.post_id, '')
                    AND COALESCE(raw.start_date, '1900-01-01') = COALESCE(dat.start_date, '1900-01-01')
                    AND COALESCE(raw.end_date, NOW()) = COALESCE(dat.end_date, NOW()))
              WHERE dat.organization_id IS NULL
                AND dat.person_id IS NULL
                AND dat.post_id IS NULL
        '''

        self.executeTransaction(find_new)

        cols = [
           'label',
           'role',
           'start_date',
           'end_date',
           'organization_id',
           'person_id',
           'post_id',
           'updated_at',
        ]

        insert_fields = ', '.join(c for c in cols)
        select_fields = ', '.join('raw.{}'.format(c) for c in cols)

        insert_new = '''
            INSERT INTO councilmatic_core_membership (
              {insert_fields}
            )
              SELECT {select_fields}
              FROM raw_membership AS raw
              JOIN new_membership AS new
                ON (raw.organization_id = new.organization_id
                    AND raw.person_id = new.person_id
                    AND COALESCE(raw.post_id, '') = COALESCE(new.post_id, '')
                    AND COALESCE(raw.start_date, '1900-01-01') = COALESCE(new.start_date, '1900-01-01')
                    AND COALESCE(raw.end_date, NOW()) = COALESCE(new.end_date, NOW()))
        '''.format(insert_fields=insert_fields,
                   select_fields=select_fields)

        self.executeTransaction(insert_new)

        new_count = self.connection.execute('select count(*) from new_membership').first().count

        self.log_message('Found {0} new membership'.format(new_count), style='SUCCESS')

    def add_new_bills(self):
        cols = [
            'ocd_id',
            'ocd_created_at',
            'ocd_updated_at',
            'description',
            'identifier',
            'bill_type',
            'classification',
            'source_url',
            'source_note',
            'subject',
            'from_organization_id',
            'full_text',
            'ocr_full_text',
            'abstract',
            'last_action_date',
            'legislative_session_id',
            'slug',
        ]

        self.add_entity_type('bill', cols=cols)

    def add_new_actions(self):
        self.executeTransaction('DROP TABLE IF EXISTS new_action')
        self.executeTransaction('''
            CREATE TABLE new_action (
                bill_id VARCHAR,
                "order" INTEGER
            )
        ''')

        find_new = '''
            INSERT INTO new_action
              SELECT
                raw.bill_id,
                raw."order"
              FROM raw_action AS raw
              LEFT JOIN councilmatic_core_action AS dat
                ON (raw.bill_id = dat.bill_id
                    AND raw."order" = dat."order")
              WHERE dat.bill_id IS NULL
                AND dat."order" IS NULL
        '''

        self.executeTransaction(find_new)

        cols = [
            'date',
            'classification',
            'description',
            'order',
            'bill_id',
            'organization_id',
        ]

        insert_fields = ', '.join('"{}"'.format(c) for c in cols)
        select_fields = ', '.join('raw."{}"'.format(c) for c in cols)

        insert_new = '''
            INSERT INTO councilmatic_core_action (
              {insert_fields},
              updated_at
            )
              SELECT {select_fields}, raw.updated_at
              FROM raw_action AS raw
              JOIN new_action AS new
                ON (raw.bill_id = new.bill_id
                    AND raw."order" = new."order")
        '''.format(insert_fields=insert_fields,
                   select_fields=select_fields)

        self.executeTransaction(insert_new)

        new_count = self.connection.execute('select count(*) from new_action').first().count

        self.log_message('Found {0} new action'.format(new_count), style='SUCCESS')

    def add_new_action_related_entity(self):
        self.executeTransaction('DROP TABLE IF EXISTS new_actionrelatedentity')
        self.executeTransaction('''
            CREATE TABLE new_actionrelatedentity (
                organization_ocd_id VARCHAR,
                person_ocd_id VARCHAR,
                action_id INTEGER
            )
        ''')

        cols = [
            'entity_type',
            'entity_name',
            'organization_ocd_id',
            'person_ocd_id',
            'action_id',
        ]

        find_new = '''
            INSERT INTO new_actionrelatedentity
              SELECT
                raw.organization_ocd_id,
                raw.person_ocd_id,
                raw.action_id
              FROM raw_actionrelatedentity AS raw
              LEFT JOIN councilmatic_core_actionrelatedentity AS dat
                ON (COALESCE(raw.organization_ocd_id, '') = COALESCE(dat.organization_ocd_id, '')
                    AND COALESCE(raw.person_ocd_id, '') = COALESCE(dat.person_ocd_id, '')
                    AND raw.action_id = dat.action_id)
              WHERE (dat.organization_ocd_id IS NULL
                     OR dat.person_ocd_id IS NULL)
                     AND dat.action_id IS NULL
        '''

        self.executeTransaction(find_new)

        insert_fields = ', '.join(c for c in cols)
        select_fields = ', '.join('raw.{}'.format(c) for c in cols)

        insert_new = '''
            INSERT INTO councilmatic_core_actionrelatedentity (
              {insert_fields}, updated_at
            )
              SELECT {select_fields}, updated_at
              FROM raw_actionrelatedentity AS raw
              JOIN new_actionrelatedentity AS new
                ON (COALESCE(raw.organization_ocd_id, '') = COALESCE(new.organization_ocd_id, '')
                    AND COALESCE(raw.person_ocd_id, '') = COALESCE(new.person_ocd_id, '')
                    AND raw.action_id = new.action_id)
        '''.format(insert_fields=insert_fields,
                   select_fields=select_fields)

        self.executeTransaction(insert_new)

        new_count = self.connection.execute('select count(*) from new_actionrelatedentity').first().count

        self.log_message('Found {0} new action related entities'.format(new_count), style='SUCCESS')

    def add_new_sponsorships(self):
        self.executeTransaction('DROP TABLE IF EXISTS new_sponsorship')
        self.executeTransaction('''
            CREATE TABLE new_sponsorship (
                classification VARCHAR,
                is_primary BOOLEAN,
                bill_id VARCHAR,
                person_id VARCHAR
            )
        ''')

        cols = [
            'classification',
            'is_primary',
            'bill_id',
            'person_id',
        ]

        find_new = '''
            INSERT INTO new_sponsorship
              SELECT
                raw.classification,
                raw.is_primary,
                raw.bill_id,
                raw.person_id
              FROM raw_sponsorship AS raw
              LEFT JOIN councilmatic_core_sponsorship AS dat
                ON (raw.classification = dat.classification
                    AND raw.is_primary = dat.is_primary
                    AND raw.bill_id = dat.bill_id
                    AND raw.person_id = dat.person_id)
              WHERE dat.classification IS NULL
                    AND dat.is_primary IS NULL
                    AND dat.bill_id IS NULL
                    AND dat.person_id IS NULL
        '''

        self.executeTransaction(find_new)

        insert_fields = ', '.join(c for c in cols)
        select_fields = ', '.join('raw.{}'.format(c) for c in cols)

        insert_new = '''
            INSERT INTO councilmatic_core_sponsorship (
              {insert_fields}, updated_at
            )
              SELECT {select_fields}, updated_at
              FROM raw_sponsorship AS raw
              JOIN new_sponsorship AS new
                ON (raw.classification = new.classification
                    AND raw.is_primary = new.is_primary
                    AND raw.bill_id = new.bill_id
                    AND raw.person_id = new.person_id)
        '''.format(insert_fields=insert_fields,
                   select_fields=select_fields)

        self.executeTransaction(insert_new)

        new_count = self.connection.execute('select count(*) from new_sponsorship').first().count

        self.log_message('Found {0} new sponsorships'.format(new_count), style='SUCCESS')

    def add_new_billdocuments(self):
        self.executeTransaction('DROP TABLE IF EXISTS new_billdocument')
        self.executeTransaction('''
            CREATE TABLE new_billdocument (
                bill_id VARCHAR,
                url VARCHAR,
                document_type VARCHAR
            )
        ''')

        cols = [
            'bill_id',
            'url',
            'document_type',
            'note',
        ]

        find_new = '''
            INSERT INTO new_billdocument
              SELECT
                raw.bill_id,
                raw.url,
                raw.document_type
              FROM raw_billdocument AS raw
              LEFT JOIN councilmatic_core_billdocument AS dat
                ON (raw.bill_id = dat.bill_id
                    AND raw.url = dat.url
                    AND raw.document_type = dat.document_type)
              WHERE dat.bill_id IS NULL
                    AND dat.url IS NULL
                    AND dat.document_type IS NULL
        '''

        self.executeTransaction(find_new)

        insert_fields = ', '.join(c for c in cols)
        select_fields = ', '.join('raw.{}'.format(c) for c in cols)

        insert_new = '''
            INSERT INTO councilmatic_core_billdocument (
              {insert_fields}, updated_at
            )
              SELECT {select_fields}, updated_at
              FROM raw_billdocument AS raw
              JOIN new_billdocument AS new
                ON (raw.bill_id = new.bill_id
                    AND raw.url = new.url
                    AND raw.document_type = new.document_type)
        '''.format(insert_fields=insert_fields,
                   select_fields=select_fields)

        self.executeTransaction(insert_new)

        new_count = self.connection.execute('select count(*) from new_billdocument').first().count

        self.log_message('Found {0} new bill documents'.format(new_count), style='SUCCESS')

    def add_new_events(self):
        cols = [
            'ocd_id',
            'ocd_created_at',
            'ocd_updated_at',
            'name',
            'description',
            'classification',
            'start_time',
            'end_time',
            'all_day',
            'status',
            'location_name',
            'location_url',
            'media_url',
            'source_url',
            'source_note',
            'slug',
        ]

        self.add_entity_type('event', cols=cols)

    def add_new_eventparticipants(self):
        self.executeTransaction('DROP TABLE IF EXISTS new_eventparticipant')
        self.executeTransaction('''
            CREATE TABLE new_eventparticipant (
                event_id VARCHAR,
                entity_type VARCHAR,
                entity_name VARCHAR
            )
        ''')

        cols = [
            'event_id',
            'entity_type',
            'entity_name',
            'note',
        ]

        find_new = '''
            INSERT INTO new_eventparticipant
              SELECT
                raw.event_id,
                raw.entity_type,
                raw.entity_name
              FROM raw_eventparticipant AS raw
              LEFT JOIN councilmatic_core_eventparticipant AS dat
                ON (raw.event_id = dat.event_id
                    AND raw.entity_type = dat.entity_type
                    AND raw.entity_name = dat.entity_name)
              WHERE dat.event_id IS NULL
                    AND dat.entity_type IS NULL
                    AND dat.entity_name IS NULL
        '''

        self.executeTransaction(find_new)

        insert_fields = ', '.join(c for c in cols)
        select_fields = ', '.join('raw.{}'.format(c) for c in cols)

        insert_new = '''
            INSERT INTO councilmatic_core_eventparticipant (
              {insert_fields}, updated_at
            )
              SELECT {select_fields}, updated_at
              FROM raw_eventparticipant AS raw
              JOIN new_eventparticipant AS new
                ON (raw.event_id = new.event_id
                    AND raw.entity_type = new.entity_type
                    AND raw.entity_name = new.entity_name)
        '''.format(insert_fields=insert_fields,
                   select_fields=select_fields)

        self.executeTransaction(insert_new)

        new_count = self.connection.execute('select count(*) from new_eventparticipant').first().count

        self.log_message('Found {0} new event participants'.format(new_count), style='SUCCESS')

    def add_new_eventdocuments(self):
        self.executeTransaction('DROP TABLE IF EXISTS new_eventdocument')
        self.executeTransaction('''
            CREATE TABLE new_eventdocument (
                event_id VARCHAR,
                url VARCHAR
            )
        ''')

        cols = [
            'event_id',
            'url',
            'full_text',
            'note'
        ]

        find_new = '''
            INSERT INTO new_eventdocument
              SELECT
                raw.event_id,
                raw.url
              FROM raw_eventdocument AS raw
              LEFT JOIN councilmatic_core_eventdocument AS dat
                ON (raw.event_id = dat.event_id
                    AND raw.url = dat.url)
              WHERE dat.event_id IS NULL
                    AND dat.url IS NULL
        '''

        self.executeTransaction(find_new)

        insert_fields = ', '.join(c for c in cols)
        select_fields = ', '.join('raw.{}'.format(c) for c in cols)

        insert_new = '''
            INSERT INTO councilmatic_core_eventdocument (
              {insert_fields}
            )
              SELECT {select_fields}
              FROM raw_eventdocument AS raw
              JOIN new_eventdocument AS new
                ON (raw.event_id = new.event_id
                    AND raw.url = new.url)
        '''.format(insert_fields=insert_fields,
                   select_fields=select_fields)

        self.executeTransaction(insert_new)

        new_count = self.connection.execute('select count(*) from new_eventdocument').first().count

        self.log_message('Found {0} new event documents'.format(new_count), style='SUCCESS')

    def add_new_event_agenda_items(self):
        self.executeTransaction('DROP TABLE IF EXISTS new_eventagendaitem')
        self.executeTransaction('''
            CREATE TABLE new_eventagendaitem (
                event_id VARCHAR,
                "order" INTEGER
            )
        ''')

        cols = [
            'order',
            'description',
            'event_id',
            'bill_id',
            'note',
            'notes',
        ]

        find_new = '''
            INSERT INTO new_eventagendaitem
              SELECT
                raw.event_id,
                raw."order"
              FROM raw_eventagendaitem AS raw
              LEFT JOIN councilmatic_core_eventagendaitem AS dat
                ON (raw.event_id = dat.event_id
                    AND raw."order" = dat."order")
              WHERE dat.event_id IS NULL
                    AND dat."order" IS NULL
        '''

        self.executeTransaction(find_new)

        insert_fields = ', '.join('"{}"'.format(c) for c in cols)
        select_fields = ', '.join('raw."{}"'.format(c) for c in cols)

        insert_new = '''
            INSERT INTO councilmatic_core_eventagendaitem (
              {insert_fields}, updated_at
            )
              SELECT {select_fields}, updated_at
              FROM raw_eventagendaitem AS raw
              JOIN new_eventagendaitem AS new
                ON (raw.event_id = new.event_id
                    AND raw."order" = new."order")
        '''.format(insert_fields=insert_fields,
                   select_fields=select_fields)

        self.executeTransaction(insert_new)
        new_count = self.connection.execute('select count(*) from new_eventagendaitem').first().count

        self.log_message('Found {0} new event agenda items'.format(new_count), style='SUCCESS')


    def populate_council_district_shapes(self):

        self.log_message('Populating boundaries ...')
        # grab boundary listing
        for boundary in settings.BOUNDARY_SET:
            bndry_set_url = bndry_base_url + '/boundaries/' + boundary
            r = session.get(bndry_set_url + '/?limit=0')
            page_json = json.loads(r.text)

            # loop through boundary listing
            for bndry_json in page_json['objects']:
                # grab boundary shape
                shape_url = bndry_base_url + bndry_json['url'] + 'shape'
                r = session.get(shape_url)
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

                print('.', end='')
                sys.stdout.flush()

    def executeTransaction(self, query, *args, **kwargs):
        trans = self.connection.begin()

        raise_exc = kwargs.get('raise_exc', True)

        try:
            self.connection.execute("SET local timezone to '{}'".format(settings.TIME_ZONE))
            if kwargs:
                self.connection.execute(query, **kwargs)
            else:
                self.connection.execute(query, *args)
            trans.commit()
        except sa.exc.ProgrammingError as e:
            # TODO: Make some kind of logger
            # logger.error(e, exc_info=True)
            trans.rollback()
            if raise_exc:
                raise e
