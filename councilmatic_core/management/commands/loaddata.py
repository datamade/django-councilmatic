import json
import re
import datetime
import os

import requests
import pytz
import psycopg2

from dateutil import parser as date_parser

from django.core.management.base import BaseCommand
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.text import slugify
from django.db.utils import IntegrityError, DataError
from django.db.models import Max
from django.db import connection

from councilmatic_core.models import Person, Bill, Organization, Action, ActionRelatedEntity, \
    Post, Membership, Sponsorship, LegislativeSession, \
    Document, BillDocument, Event, EventParticipant, EventDocument, \
    EventAgendaItem, AgendaItemBill

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
        
        parser.add_argument('--import_only',
                            action='store_true',
                            default=False,
                            help='Load already downloaded OCD data')
    
    def handle(self, *args, **options):
        
        db_conn = settings.DATABASES['default']
        self.db_conn_kwargs = {
            'database': db_conn['NAME'],
            'user': db_conn['USER'],
            'password': db_conn['PASSWORD'],
            'host': db_conn['HOST'],
            'port': db_conn['PORT'],
        }
        
        self.this_folder = os.path.abspath(os.path.dirname(__file__))
        
        self.organizations_folder = os.path.join(self.this_folder, 'organizations', settings.APP_NAME)
        self.posts_folder = os.path.join(self.this_folder, 'posts', settings.APP_NAME)
        self.bills_folder = os.path.join(self.this_folder, 'bills', settings.APP_NAME)
        self.people_folder = os.path.join(self.this_folder, 'people', settings.APP_NAME)
        self.events_folder = os.path.join(self.this_folder, 'events', settings.APP_NAME)

        if options['update_since']:
            self.update_since = date_parser.parse(options['update_since'])

        if options['endpoint'] == 'organizations':
            
            if not options['import_only']:
                self.grab_organizations()
            
            self.insert_raw_organizations(delete=options['delete'])
            self.insert_raw_posts(delete=options['delete'])
            
            self.update_existing_organizations()
            self.update_existing_posts()
            

            self.add_new_organizations()
            self.add_new_posts()

            print("\ndone!", datetime.datetime.now())

        elif options['endpoint'] == 'bills':
            
            self.create_legislative_sessions()

            if not options['import_only']:
                self.grab_bills()
            
            # self.insert_raw_bills(delete=options['delete'])
            # self.insert_raw_actions(delete=options['delete'])
            # 
            # self.update_existing_bills()
            # self.update_existing_actions()
            # 
            # self.add_new_bills()
            # self.add_new_actions()
            
            # self.insert_raw_action_related_entity(delete=options['delete'])
            # self.insert_raw_sponsorships(delete=options['delete'])
            # self.insert_raw_billdocuments(delete=options['delete'])
            
            self.update_existing_action_related_entity()
            self.update_existing_sponsorships()
            self.update_existing_billdocuments()
            

            print("\ndone!", datetime.datetime.now())

        elif options['endpoint'] == 'people':
            if not options['import_only']:
                self.grab_people()
                print("\ndone!", datetime.datetime.now())
            
            self.insert_raw_people(delete=options['delete'])
            self.insert_raw_memberships(delete=options['delete'])
            
            self.update_existing_people()
            self.update_existing_memberships()
            
            self.add_new_people()
            self.add_new_memberships()

        elif options['endpoint'] == 'events':
            self.grab_events(delete=options['delete'])
            print("\ndone!", datetime.datetime.now())

        else:
            print("\n** loading all data types! **\n")
            
            if not options['import_only']:
                self.grab_organizations()
                self.grab_people()
                self.grab_bills(delete=options['delete'])
                self.grab_events(delete=options['delete'])
            
            self.insert_raw_organizations(delete=options['delete'])
            self.insert_raw_posts(delete=options['delete'])
            self.insert_raw_people(delete=options['delete'])
            self.insert_raw_memberships(delete=options['delete'])
            
            self.update_existing_organizations()
            self.update_existing_posts()
            self.update_existing_people()
            self.update_existing_memberships()
            
            self.add_new_organizations()
            self.add_new_posts()
            self.add_new_people()
            self.add_new_memberships()

            print("\ndone!", datetime.datetime.now())
    
    #########################
    ###                   ###
    ### DOWNLOAD FROM OCD ###
    ###                   ###
    #########################

    def grab_organizations(self):
        print("\n\nLOADING ORGANIZATIONS", datetime.datetime.now())
        
        try:
            os.mkdir(os.path.join(self.organizations_folder))
        except OSError:
            pass
        
        try:
            os.mkdir(os.path.join(self.posts_folder))
        except OSError:
            pass

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

    def grab_organization_posts(self, org_dict):
        url = base_url + '/organizations/'

        r = requests.get(url, params=org_dict)
        page_json = json.loads(r.text)
        organization_ocd_id = page_json['results'][0]['id']

        url = base_url + '/' + organization_ocd_id + '/'
        r = requests.get(url)
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

        for child in page_json['children']:
            self.grab_organization_posts({'id': child['id']})
    
    def grab_people(self):
        # find people associated with existing organizations & bills

        print("\n\nLOADING PEOPLE", datetime.datetime.now())
        
        try:
            os.mkdir(os.path.join(self.people_folder))
        except OSError:
            pass
        
        for organization_json in os.listdir(self.organizations_folder):
            
            org_info = json.load(open(os.path.join(self.organizations_folder, organization_json)))
            
            for membership_json in org_info['memberships']:
                person_json = self.grab_person_memberships(membership_json['person']['id'])
                
                person_uuid = person_json['id'].split('/')[-1]
                person_filename = '{}.json'.format(person_uuid)
                
                with open(os.path.join(self.people_folder, person_filename), 'w') as f:
                    f.write(json.dumps(person_json))
    
    def grab_person_memberships(self, person_id):
        # this grabs a person and all their memberships
        
        url = base_url + '/' + person_id + '/'
        r = requests.get(url)
        page_json = json.loads(r.text)

        # save image to disk
        if page_json['image']:
            r = requests.get(page_json['image'], verify=False)
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

        print("\n\nLOADING BILLS", datetime.datetime.now())
        
        try:
            os.mkdir(self.bills_folder)
        except OSError:
            pass

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

        for page_num in range(page_json['meta']['max_page']):

            query_params['page'] = int(page_num) + 1
            result_page = requests.get(search_url, params=query_params)

            for result in result_page.json()['results']:

                bill_url = '{base}/{bill_id}/'.format(
                    base=base_url, bill_id=result['id'])
                bill_detail = requests.get(bill_url)
                
                bill_json = bill_detail.json()
                ocd_uuid = bill_json['id'].split('/')[-1]
                bill_filename = '{}.json'.format(ocd_uuid)
                
                with open(os.path.join(self.bills_folder, bill_filename), 'w') as f:
                    f.write(json.dumps(bill_json))

    ###########################
    ###                     ###
    ### INSERT RAW ENTITIES ###
    ###                     ###
    ###########################
    
    def remake_raw(self, entity_type, delete=False):
        with connection.cursor() as curs:
            
            if delete:
                curs.execute(
                    'TRUNCATE councilmatic_core_{} CASCADE'.format(entity_type))
                
                print("deleted all {}".format(entity_type))
            
            curs.execute('DROP TABLE IF EXISTS raw_{}'.format(entity_type))
            
            curs.execute(''' 
                CREATE TABLE raw_{0} AS (
                  SELECT * FROM councilmatic_core_{0}
                ) WITH NO DATA
            '''.format(entity_type))

    def setup_raw(self, entity_type, delete=False):
        
        self.remake_raw(entity_type, delete=delete)

        with connection.cursor() as curs:
            
            curs.execute('''
                ALTER TABLE raw_{} ADD PRIMARY KEY (ocd_id)
            '''.format(entity_type))
            
            curs.execute('''
                ALTER TABLE raw_{} 
                ALTER COLUMN updated_at SET DEFAULT NOW()
            '''.format(entity_type))
    
    def create_legislative_sessions(self):
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
    
    def insert_raw_organizations(self, delete=False):

        self.setup_raw('organization', delete=delete)

        inserts = []
        
        insert_fmt = ''' 
            INSERT INTO raw_organization (
                ocd_id,
                name,
                classification,
                source_url,
                slug,
                parent_id
            ) VALUES {}
            '''

        with connection.cursor() as curs:
            for organization_json in os.listdir(self.organizations_folder):
                
                org_info = json.load(open(os.path.join(self.organizations_folder, organization_json)))
                
                source_url = None 
                if org_info['sources']:
                    source_url = org_info['sources'][0]['url']
                
                parent_ocd_id = None
                if org_info['parent']:
                    parent_ocd_id = org_info['parent']['id']
                
                ocd_part = org_info['id'].rsplit('-', 1)[1]
                slug = '{0}-{1}'.format(slugify(org_info['name']),ocd_part)

                insert = (
                    org_info['id'],
                    org_info['name'],
                    org_info['classification'],
                    source_url,
                    slug,
                    parent_ocd_id,
                )
                
                inserts.append(insert)

            if inserts:
                template = ','.join(['%s'] * len(inserts))
                curs.execute(insert_fmt.format(template), inserts)
            
            curs.execute('select count(*) from raw_organization')
            raw_count = curs.fetchone()[0]
    
        self.stdout.write(self.style.SUCCESS('Found {0} organizations'.format(raw_count)))

    def insert_raw_posts(self, delete=False):
        
        self.setup_raw('post', delete=delete)
        
        inserts = []

        insert_fmt = ''' 
            INSERT INTO raw_post (
                ocd_id,
                label,
                role,
                organization_id,
                division_ocd_id
            ) VALUES {}
        '''

        with connection.cursor() as curs:
            for post_json in os.listdir(self.posts_folder):
                
                post_info = json.load(open(os.path.join(self.posts_folder, post_json)))
                
                insert = (
                    post_info['id'],
                    post_info['label'],
                    post_info['role'],
                    post_info['org_ocd_id'],
                    post_info['division_id'],
                )
                
                inserts.append(insert)

            if inserts:
                template = ','.join(['%s'] * len(inserts))
                curs.execute(insert_fmt.format(template), inserts)

            curs.execute('select count(*) from raw_post')
            raw_count = curs.fetchone()[0]
        
        self.stdout.write(self.style.SUCCESS('Found {0} posts'.format(raw_count)))
    
    def insert_raw_people(self, delete=False):

        self.setup_raw('person', delete=delete)

        inserts = []

        insert_fmt = ''' 
            INSERT INTO raw_person (
                ocd_id,
                name,
                headshot,
                source_url,
                source_note,
                website_url,
                email,
                slug
            ) VALUES {}
        '''

        with connection.cursor() as curs:
            for person_json in os.listdir(self.people_folder):
                
                person_info = json.load(open(os.path.join(self.people_folder, person_json)))
                
                source_url = None 
                if person_info['sources']:
                    source_url = person_info['sources'][0]['url']
                
                source_note = None 
                if person_info['sources']:
                    source_note = person_info['sources'][0]['note']
                
                ocd_part = person_info['id'].rsplit('-', 1)[1]
                slug = '{0}-{1}'.format(slugify(person_info['name']),ocd_part)
                
                insert = (
                    person_info['id'],
                    person_info['name'],
                    person_info['image'],
                    source_url,
                    source_note,
                    person_info['website_url'],
                    person_info['email'],
                    slug
                )
                
                inserts.append(insert)

            if inserts:
                template = ','.join(['%s'] * len(inserts))
                curs.execute(insert_fmt.format(template), inserts)

            curs.execute('select count(*) from raw_person')
            raw_count = curs.fetchone()[0]
        
        self.stdout.write(self.style.SUCCESS('Found {0} people'.format(raw_count)))
    
    def insert_raw_memberships(self, delete=False):

        self.remake_raw('membership', delete=delete)
        
        with connection.cursor() as curs:
            
            curs.execute('''
                ALTER TABLE raw_membership 
                ALTER COLUMN updated_at SET DEFAULT NOW()
            ''')

        inserts = []

        insert_fmt = ''' 
            INSERT INTO raw_membership (
                label,
                role,
                start_date,
                end_date,
                organization_id,
                person_id,
                post_id
            ) VALUES {}
        '''

        with connection.cursor() as curs:
            for person_json in os.listdir(self.people_folder):
                
                person_info = json.load(open(os.path.join(self.people_folder, person_json)))

                for membership_json in person_info['memberships']:
                    
                    end_date = parse_date(membership_json['end_date'])
                    
                    start_date = parse_date(membership_json['start_date'])
                    
                    post_id = None
                    if membership_json['post']:
                        post_id = membership_json['post']['id']

                    insert = (
                        membership_json['label'],
                        membership_json['role'],
                        start_date,
                        end_date,
                        membership_json['organization']['id'],
                        person_info['id'],
                        post_id,
                    )
                    
                    inserts.append(insert)

            if inserts:
                template = ','.join(['%s'] * len(inserts))
                curs.execute(insert_fmt.format(template), inserts)

            curs.execute('select count(*) from raw_membership')
            raw_count = curs.fetchone()[0]
        
        self.stdout.write(self.style.SUCCESS('Found {0} memberships'.format(raw_count)))
    
    def insert_raw_bills(self, delete=False):
        
        self.setup_raw('bill', delete=delete)
        
        inserts = []
        
        insert_fmt = ''' 
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
            ) VALUES {}
            '''

        with connection.cursor() as curs:
            for bill_json in os.listdir(self.bills_folder):
                
                bill_info = json.load(open(os.path.join(self.bills_folder, bill_json)))
                
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
                

                ocd_part = bill_info['id'].rsplit('-', 1)[1]
                slug = '{0}-{1}'.format(slugify(bill_info['identifier']),ocd_part)

                insert = (
                    bill_info['id'],
                    bill_info['created_at'],
                    bill_info['updated_at'],
                    bill_info['title'],
                    bill_info['identifier'],
                    bill_info['classification'][0],
                    source_url,
                    bill_info['sources'][0]['note'],
                    bill_info['from_organization']['id'],
                    full_text,
                    ocr_full_text,
                    abstract,
                    bill_info['legislative_session']['identifier'],
                    bill_type,
                    subject,
                    slug,
                )
                
                inserts.append(insert)

                if inserts and len(inserts) % 10000 == 0:
                    template = ','.join(['%s'] * len(inserts))
                    curs.execute(insert_fmt.format(template), inserts)
                    
                    inserts = []
            
            if inserts:
                template = ','.join(['%s'] * len(inserts))
                curs.execute(insert_fmt.format(template), inserts)
            
            curs.execute('select count(*) from raw_bill')
            raw_count = curs.fetchone()[0]
    
        self.stdout.write(self.style.SUCCESS('Found {0} bill'.format(raw_count)))
    
    def insert_raw_actions(self, delete=False):
        
        self.remake_raw('action', delete=delete)
        
        with connection.cursor() as curs:
            curs.execute('''
                ALTER TABLE raw_action 
                ALTER COLUMN updated_at SET DEFAULT NOW()
            ''')

        inserts = []
        
        insert_fmt = ''' 
            INSERT INTO raw_action (
                date,
                classification,
                description,
                organization_id,
                bill_id,
                "order"
            ) VALUES {}
            '''

        with connection.cursor() as curs:
            for bill_json in os.listdir(self.bills_folder):
                
                bill_info = json.load(open(os.path.join(self.bills_folder, bill_json)))

                for order, action in enumerate(bill_info['actions']):
                    
                    classification = None
                    if action['classification']:
                        classification = action['classification'][0]
                    
                    action_date = app_timezone.localize(date_parser.parse(action['date']))
                    
                    insert = (
                        action_date,
                        classification,
                        action['description'],
                        action['organization']['id'],
                        bill_info['id'],
                        order
                    )
                    
                    inserts.append(insert)
                    
                    if inserts and len(inserts) % 10000 == 0:
                        template = ','.join(['%s'] * len(inserts))
                        curs.execute(insert_fmt.format(template), inserts)
                        
                        inserts = []
            
            if inserts:
                template = ','.join(['%s'] * len(inserts))
                curs.execute(insert_fmt.format(template), inserts)
            
            curs.execute('select count(*) from raw_action')
            raw_count = curs.fetchone()[0]
    
        self.stdout.write(self.style.SUCCESS('Found {0} actions'.format(raw_count)))
    
    def insert_raw_action_related_entity(self, delete=False):

        self.remake_raw('actionrelatedentity', delete=delete)
        
        with connection.cursor() as curs:
            curs.execute('''
                ALTER TABLE raw_actionrelatedentity 
                ALTER COLUMN updated_at SET DEFAULT NOW()
            ''')

        inserts = []
        
        insert_fmt = ''' 
            INSERT INTO raw_actionrelatedentity (
                entity_type,
                entity_name,
                organization_ocd_id,
                person_ocd_id,
                action_id
            ) VALUES {}
            '''
        
        read_cursor = connection.cursor()

        with connection.cursor() as curs:

            read_cursor.execute(''' 
                SELECT id, bill_id, "order" FROM councilmatic_core_action
            ''')

            for action in read_cursor:
                
                action_id, bill_id, order = action

                ocd_uuid = bill_id.split('/')[-1]
                bill_filename = '{}.json'.format(ocd_uuid)
                
                bill_info = json.load(open(os.path.join(self.bills_folder, bill_filename)))
                
                action = bill_info['actions'][order]

                for related_entity in action['related_entities']:
                    
                    person_id = None
                    organization_id = None

                    if related_entity['entity_type'] == 'organization':

                        organization_id = related_entity['organization_id']
                        
                        if not organization_id:
                            curs.execute(""" 
                                SELECT ocd_id 
                                FROM councilmatic_core_organization
                                WHERE name = %s
                                LIMIT 1
                            """, [related_entity['name']])
                            
                            for row in curs:
                                organization_id = row[0]
                    
                    elif related_entity['entity_type'] == 'person':

                        person_id = related_entity['person_id']
                        
                        if not person_id:
                            curs.execute(""" 
                                SELECT ocd_id 
                                FROM councilmatic_core_person
                                WHERE name = %s
                                LIMIT 1
                            """, [related_entity['name']])

                            for row in curs:
                                person_id = row[0]
                    
                    insert = (
                        related_entity['entity_type'],
                        related_entity['name'],
                        organization_id,
                        person_id,
                        action_id,
                    )
                    
                    inserts.append(insert)
                    
                    if inserts and len(inserts) % 10000 == 0:
                        template = ','.join(['%s'] * len(inserts))
                        curs.execute(insert_fmt.format(template), inserts)
                        
                        inserts = []
            
            if inserts:
                template = ','.join(['%s'] * len(inserts))
                curs.execute(insert_fmt.format(template), inserts)
            
            curs.execute('select count(*) from raw_actionrelatedentity')
            raw_count = curs.fetchone()[0]
    
        self.stdout.write(self.style.SUCCESS('Found {0} action related entities'.format(raw_count)))
    
    def insert_raw_sponsorships(self, delete=False):
        
        self.remake_raw('sponsorship', delete=delete)
        
        with connection.cursor() as curs:
            curs.execute('''
                ALTER TABLE raw_sponsorship 
                ALTER COLUMN updated_at SET DEFAULT NOW()
            ''')
            
            curs.execute(''' 
                CREATE TABLE raw_sponsorship_temp AS (
                    SELECT * FROM councilmatic_core_sponsorship
                ) WITH NO DATA
            ''')
        
            curs.execute('''
                ALTER TABLE raw_sponsorship_temp 
                ALTER COLUMN updated_at SET DEFAULT NOW()
            ''')

        inserts = []
        
        insert_fmt = ''' 
            INSERT INTO raw_sponsorship_temp (
                classification,
                is_primary,
                bill_id,
                person_id
            ) VALUES {}
            '''
        
        with connection.cursor() as curs:
            for bill_json in os.listdir(self.bills_folder):
                
                bill_info = json.load(open(os.path.join(self.bills_folder, bill_json)))
                
                for sponsorship in bill_info['sponsorships']:
                    
                    insert = (
                        sponsorship['classification'],
                        sponsorship['primary'],
                        bill_info['id'],
                        sponsorship['entity_id'],
                    )
                    
                    inserts.append(insert)
                    
                    if inserts and len(inserts) % 10000 == 0:
                        template = ','.join(['%s'] * len(inserts))
                        curs.execute(insert_fmt.format(template), inserts)
                        
                        inserts = []
            
            if inserts:
                template = ','.join(['%s'] * len(inserts))
                curs.execute(insert_fmt.format(template), inserts)
        
        # Temproary measure to make sure we can actually update things.
        with connection.cursor() as curs:
            curs.execute(''' 
                INSERT INTO raw_sponsorship 
                  SELECT DISTINCT ON (classification, is_primary, bill_id, person_id)
                  *
                  FROM raw_sponsorship_temp
            ''')

            curs.execute('select count(*) from raw_sponsorship')
            raw_count = curs.fetchone()[0]
    
        self.stdout.write(self.style.SUCCESS('Found {0} sponsorships'.format(raw_count)))

    def insert_raw_billdocuments(self, delete=False):
        
        self.remake_raw('billdocument', delete=delete)
        
        with connection.cursor() as curs:
            curs.execute('''
                ALTER TABLE raw_billdocument 
                ALTER COLUMN updated_at SET DEFAULT NOW()
            ''')
            
        inserts = []

        insert_fmt = ''' 
            INSERT INTO raw_billdocument (
                note,
                url, 
                bill_id,
                document_type
            ) VALUES {}
        '''
        
        count = 0
        with connection.cursor() as curs:
            for bill_json in os.listdir(self.bills_folder):
                
                bill_info = json.load(open(os.path.join(self.bills_folder, bill_json)))
                
                for document in bill_info['documents']:

                    insert = (
                        document['note'],
                        document['links'][0]['url'],
                        bill_info['id'],
                        'A',
                    )
                    
                    inserts.append(insert)

                for document in bill_info['versions']:

                    insert = (
                        document['note'],
                        document['links'][0]['url'],
                        bill_info['id'],
                        'V',
                    )

                    inserts.append(insert)

                if inserts and len(inserts) % 10000 == 0:
                    template = ','.join(['%s'] * len(inserts))
                    curs.execute(insert_fmt.format(template), inserts)
                    
                    inserts = []
            
            if inserts:
                template = ','.join(['%s'] * len(inserts))
                curs.execute(insert_fmt.format(template), inserts)
                
            curs = connection.cursor()
            curs.execute('select count(*) from raw_billdocument')
            raw_count = curs.fetchone()[0]
    
        self.stdout.write(self.style.SUCCESS('Found {0} bill attachments and versions'.format(raw_count)))


    ################################
    ###                          ###
    ### UPDATE EXISTING ENTITIES ###
    ###                          ###
    ################################
    
    def setup_update(self, entity_type):
        with connection.cursor() as curs:
            
            curs.execute('DROP TABLE IF EXISTS change_{}'.format(entity_type))
            curs.execute(''' 
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
                ((raw."{0}" IS NOT NULL OR dat."{0}" IS NOT NULL) AND raw."{0}" <> dat."{0}")
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
        
        with connection.cursor() as curs:
            curs.execute(find_changes)
            curs.execute('select count(*) from change_{}'.format(entity_type))
            change_count = curs.fetchone()[0]

        with connection.cursor() as curs:
            curs.execute(update_dat)

        self.stdout.write(self.style.SUCCESS('Found {0} changed {1}'.format(change_count, entity_type)))

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
        
        with connection.cursor() as curs:
            
            curs.execute('DROP TABLE IF EXISTS change_membership')
            curs.execute(''' 
                CREATE TABLE change_membership (
                    organization_id VARCHAR,
                    person_id VARCHAR,
                    post_id VARCHAR,
                    start_date,
                    end_date
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
                raw_start_date,
                raw.end_date
              FROM raw_membership AS raw
              JOIN councilmatic_core_membership AS dat
                ON (raw.organization_id = dat.organization_id
                    AND raw.person_id = dat.person_id
                    AND COALESCE(raw.post_id, '') = COALESCE(dat.post_id, '')
                    AND COALESCE(raw.start_date, '') = COALESCE(dat.start_date, '')
                    AND COALESCE(raw.end_date, '') = COALESCE(dat.end_date, ''))
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
                    AND COALESCE(raw.start_date, '') = COALESCE(change.start_date, '')
                    AND COALESCE(raw.end_date, '') = COALESCE(change.end_date, ''))
            ) AS s
            WHERE councilmatic_core_membership.organization_id = s.organization_id
              AND councilmatic_core_membership.person_id = s.person_id
              AND COALESCE(councilmatic_core_membership.post_id, '') = COALESCE(s.post_id, '')
              AND COALESCE(councilmatic_core_membership.start_date, '') = COALESCE(s.start_date, '')
              AND COALESCE(councilmatic_core_membership.end_date, '') = COALESCE(s.end_date, '')
        '''.format(set_values=set_values, 
                   fields=fields)
        
        with connection.cursor() as curs:
            curs.execute(find_changes)
            curs.execute('select count(*) from change_membership')
            change_count = curs.fetchone()[0]

        with connection.cursor() as curs:
            curs.execute(update_dat)

        self.stdout.write(self.style.SUCCESS('Found {0} changed membership'.format(change_count)))
    
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
        
        with connection.cursor() as curs:
            
            curs.execute('DROP TABLE IF EXISTS change_action')
            curs.execute(''' 
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
        
        with connection.cursor() as curs:
            curs.execute(find_changes)
            curs.execute('select count(*) from change_action')
            change_count = curs.fetchone()[0]

        with connection.cursor() as curs:
            curs.execute(update_dat)

        self.stdout.write(self.style.SUCCESS('Found {0} changed action'.format(change_count)))
    
    def update_existing_action_related_entity(self):
        with connection.cursor() as curs:
            
            curs.execute('DROP TABLE IF EXISTS change_actionrelatedentity')
            curs.execute(''' 
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

        with connection.cursor() as curs:
            curs.execute(find_changes)
            curs.execute('select count(*) from change_actionrelatedentity')
            change_count = curs.fetchone()[0]

        with connection.cursor() as curs:
            curs.execute(update_dat)

        self.stdout.write(self.style.SUCCESS('Found {0} changed action related entities'.format(change_count)))

    def update_existing_sponsorships(self):
        with connection.cursor() as curs:
            
            curs.execute('DROP TABLE IF EXISTS change_sponsorship')
            curs.execute(''' 
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

        with connection.cursor() as curs:
            curs.execute(find_changes)
            curs.execute('select count(*) from change_sponsorship')
            change_count = curs.fetchone()[0]

        with connection.cursor() as curs:
            curs.execute(update_dat)

        self.stdout.write(self.style.SUCCESS('Found {0} changed sponsorships'.format(change_count)))

    def update_existing_billdocuments(self):
        with connection.cursor() as curs:
            
            curs.execute('DROP TABLE IF EXISTS change_billdocument')
            curs.execute(''' 
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
              FROM raw_bill_document AS raw
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

        with connection.cursor() as curs:
            curs.execute(find_changes)
            curs.execute('select count(*) from change_billdocument')
            change_count = curs.fetchone()[0]

        with connection.cursor() as curs:
            curs.execute(update_dat)

        self.stdout.write(self.style.SUCCESS('Found {0} changed bill documents'.format(change_count)))


    ########################
    ###                  ###
    ### ADD NEW ENTITIES ###
    ###                  ###
    ########################

    def add_entity_type(self, entity_type, cols=[], extra_cols=['updated_at']):
        with connection.cursor() as curs:
            
            curs.execute('DROP TABLE IF EXISTS new_{}'.format(entity_type))
            curs.execute(''' 
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

        with connection.cursor() as curs:
            curs.execute(find_new)
            curs.execute('select count(*) from new_{}'.format(entity_type))
            new_count = curs.fetchone()[0]
        
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
        
        with connection.cursor() as curs:
            curs.execute(insert_new)

        self.stdout.write(self.style.SUCCESS('Found {0} new {1}'.format(new_count, entity_type)))
    
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
        with connection.cursor() as curs:
            
            curs.execute('DROP TABLE IF EXISTS new_membership')
            curs.execute(''' 
                CREATE TABLE new_membership (
                    organization_id VARCHAR,
                    person_id VARCHAR,
                    post_id VARCHAR
                )
            ''')
        
        find_new = ''' 
            INSERT INTO new_membership
              SELECT 
                raw.organization_id,
                raw.person_id,
                raw.post_id
              FROM raw_membership AS raw
              LEFT JOIN councilmatic_core_membership AS dat
                ON (raw.organization_id = dat.organization_id
                    AND raw.person_id = dat.person_id
                    AND COALESCE(raw.post_id, '') = COALESCE(dat.post_id, ''))
              WHERE dat.organization_id IS NULL
                AND dat.person_id IS NULL
                AND dat.post_id IS NULL
        '''

        with connection.cursor() as curs:
            curs.execute(find_new)
            curs.execute('select count(*) from new_membership')
            new_count = curs.fetchone()[0]
        
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
                    AND COALESCE(raw.post_id, '') = COALESCE(new.post_id, ''))
        '''.format(insert_fields=insert_fields,
                   select_fields=select_fields)
        
        with connection.cursor() as curs:
            curs.execute(insert_new)

        self.stdout.write(self.style.SUCCESS('Found {0} new membership'.format(new_count)))
    
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
        with connection.cursor() as curs:
            
            curs.execute('DROP TABLE IF EXISTS new_action')
            curs.execute(''' 
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

        with connection.cursor() as curs:
            curs.execute(find_new)
            curs.execute('select count(*) from new_action')
            new_count = curs.fetchone()[0]
        
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
        
        with connection.cursor() as curs:
            curs.execute(insert_new)

        self.stdout.write(self.style.SUCCESS('Found {0} new action'.format(new_count)))
    
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
