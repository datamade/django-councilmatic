from django.db import models
from datetime import datetime
from django.core.exceptions import ImproperlyConfigured
import pytz
from django.conf import settings
import inspect
import importlib

if not hasattr(settings, 'OCD_CITY_COUNCIL_ID'):
    raise ImproperlyConfigured('You must define a OCD_COUNCIL_ID in settings.py')

if not hasattr(settings, 'CITY_COUNCIL_NAME'):
    raise ImproperlyConfigured('You must define a CITY_COUNCIL_NAME in settings.py')

MANUAL_HEADSHOTS = settings.MANUAL_HEADSHOTS if hasattr(settings, 'MANUAL_HEADSHOTS') else {}

app_timezone = pytz.timezone(settings.TIME_ZONE)

bill_document_choices = (
    ('A', 'Attachment'),
    ('V', 'Version'),
)


def override_relation(base_model):
    
    models_module = '{0}.models'.format(settings.APP_NAME)
    app_models = importlib.import_module(models_module)
    
    overridden = base_model
    for name, member in inspect.getmembers(app_models):
        
        try:
            if issubclass(member, base_model.__class__):
                module = __import__(models_module, globals(), locals(), [name])
                
                overridden = getattr(module, name)()

                attrs = [f.attname for f in base_model.__class__._meta.fields] + ['_state']
                for attr in attrs:
                    setattr(overridden, attr, getattr(base_model, attr))
                

        except TypeError:
            pass
    
    return overridden


class Person(models.Model):
    ocd_id = models.CharField(max_length=100, unique=True, null=True)
    name = models.CharField(max_length=100)
    headshot = models.CharField(max_length=255, blank=True)
    source_url = models.CharField(max_length=255, blank=True)
    source_note = models.CharField(max_length=255, blank=True)
    website_url = models.CharField(max_length=255, blank=True)
    email = models.CharField(max_length=255, blank=True)
    slug = models.CharField(max_length=255, unique=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def latest_council_membership(self):
        city_council_id = settings.OCD_CITY_COUNCIL_ID
        filter_kwarg = {'_organization__ocd_id': city_council_id}
        
        city_council_memberships = self.memberships.filter(**filter_kwarg)
        
        if city_council_memberships.count():
            return city_council_memberships.order_by('-start_date', '-end_date').first()
        
        return None

    @property
    def current_council_seat(self):
        m = self.latest_council_membership
        if m and m.post:
            if self == m.post.current_member.person:
                return m.post.label
        return ''

    @property
    def latest_council_seat(self):
        m = self.latest_council_membership
        if m:
            return m.post.label
        return ''

    @property
    def is_speaker(self):
        return True if self.memberships.filter(role='Speaker').first() else False   

    @property
    def default_headshot_path(self):
        return settings.DEFAULT_HEADSHOT_PATH(self) if hasattr(settings, 'DEFAULT_HEADSHOT_PATH') else None

    @property
    def headshot_url(self):
        if self.slug in MANUAL_HEADSHOTS:
            return '/static/images/' + MANUAL_HEADSHOTS[self.slug]['image']
        elif self.default_headshot_path:
            return self.default_headshot_path
        elif self.headshot:
            return '/static/images/' + self.ocd_id + ".jpg"
        else:
            return '/static/images/headshot_placeholder.png'

    @property
    def headshot_source(self):
        if self.slug in MANUAL_HEADSHOTS:
            return MANUAL_HEADSHOTS[self.slug]['source']
        elif self.headshot:
            return settings.CITY_VOCAB['SOURCE']
        else:
            return None

    @property
    def link_html(self):
        # if person is a city council member
        if self.ocd_id and self.slug:
            return '<a href="/person/'+self.slug+'/" title="More on '+self.name+'">'+self.name+'</a>'
        # otherwise, don't make a link
        else:
            return self.name

    @property
    def primary_sponsorships(self):
        return self.sponsorships.filter(is_primary=True)

    @property
    def chair_role_memberships(self):
        if hasattr(settings, 'COMMITTEE_CHAIR_TITLE'):
            return self.memberships.filter(role=settings.COMMITTEE_CHAIR_TITLE).filter(_organization__name__startswith='Committee')
        else:
            return None

    @property
    def member_role_memberships(self):
        if hasattr(settings, 'COMMITTEE_MEMBER_TITLE'):
            return self.memberships.filter(role=settings.COMMITTEE_MEMBER_TITLE).filter(_organization__name__startswith='Committee')
        else:
            return None

class Bill(models.Model):
    ocd_id = models.CharField(max_length=100, unique=True)
    ocd_created_at = models.DateTimeField(default=None)
    ocd_updated_at = models.DateTimeField(default=None)
    description = models.TextField()
    identifier = models.CharField(max_length=50)
    bill_type = models.CharField(max_length=50)
    classification = models.CharField(max_length=100)
    source_url = models.CharField(max_length=255)
    source_note = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255, blank=True)

    _from_organization = models.ForeignKey('Organization', 
                                           related_name='bills', 
                                           null=True,
                                           db_column='from_organization_id')

    full_text = models.TextField(blank=True)
    ocr_full_text = models.TextField(blank=True)
    abstract = models.TextField(blank=True)
    last_action_date = models.DateTimeField(default=None, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    _legislative_session = models.ForeignKey('LegislativeSession', 
                                             related_name='bills', 
                                             null=True,
                                             db_column='legislative_session_id')
    
    slug = models.CharField(max_length=255, unique=True)
    
    @property
    def from_organization(self):
        return override_relation(self._from_organization)

    @property
    def legislative_session(self):
        return override_relation(self._legislative_session)

    def __str__(self):
        return self.friendly_name

    @property
    def controlling_body(self):
        """
        grabs the organization that's currently 'responsible' for a bill
        """

        if self.current_action:
            related_orgs = self.current_action.related_entities.filter(entity_type='organization').all()
            # when a bill is referred from city council
            # to a committee, controlling body is the organization
            # the bill was referred to (a related org)
            if related_orgs:
                controlling_bodies = [Organization.objects.get(ocd_id=org.organization_ocd_id) for org in related_orgs]
                return controlling_bodies
            # otherwise, the controlling body is usually whatever organization
            # performed the most recent action (this is the case most of the time)
            else:
                return [self.current_action.organization]
        else:
            return None

    @property
    def last_action_org(self):
        """
        grabs whatever organization performed the most recent action
        """
        return self.current_action.organization if self.current_action else None

    @property
    def current_action(self):
        """
        grabs the most recent action on a bill
        """
        return self.actions.all().order_by('-order').first() if self.actions.all() else None

    @property
    def first_action(self):
        """
        grabs the first action on a bill
        """
        return self.actions.all().order_by('order').first() if self.actions.all() else None

    @property
    def date_passed(self):
        return self.actions.filter(classification='passage').order_by('-order').first().date if self.actions.all() else None

    @property
    def friendly_name(self):
        """
        the bill title/headers displayed throughout the site (bill listings, bill detail pages)

        by default this returns the bill identifier - override this in
        custom subclass to construct a friendly name that makes sense locally
        """
        return self.identifier

    @property
    def primary_sponsor(self):
        """
        grabs the primary sponsorship for a bill
        """
        return self.sponsorships.filter(is_primary=True).first()

    @property
    def pseudo_topics(self):
        """
        returns a list of artificial topics for a bill, from the committees 
        that have been involved in the bill's history (the actions)

        this serves as a backup when there isn't data on the real topics, 
        so that bill listings can still have some useful tags populated
        """
        if self.actions.all():
            
            orgs = set([a.organization.name for a in self.actions.all() if \
                       (a.organization.name !='Mayor' and \
                        a.organization.name != settings.CITY_COUNCIL_NAME)])

            if not orgs and self.controlling_body and \
                    self.controlling_body[0].name != settings.CITY_COUNCIL_NAME:

                orgs = self.controlling_body
            
            return list(orgs)
        else:
            return None

    @property
    def topics(self):
        """
        returns a list of topics for a bill

        override this in custom subclass for richer topic logic
        """
        return None

    @property
    def addresses(self):
        """
        returns a list of relevant addresses for a bill

        override this in custom subclass
        """
        return []

    @property
    def inferred_status(self):
        """
        infers bill status, to be displayed in colored labels next to bill names

        override this in custom subclass w/ richer logic for determining
        bill status, e.g. active, passed, approved, failed, stale
        """
        return None

    @property
    def listing_description(self):
        if self.abstract:
            return self.abstract
        return self.description

    @property
    def full_text_doc_url(self):
        """
        override this if instead of having full text as string stored in
        full_text, it is a PDF document that you can embed on the page
        """
        return None

    @property
    def attachments(self):
        """
        grabs that documents that are attachments (as opposed to versions)
        """
        return self.documents.filter(document_type='A').all()

    def get_last_action_date(self):
        """
        grabs date of most recent activity on a bill
        """
        return self.actions.all().order_by('-order').first().date if self.actions.all() else None

    @classmethod
    def bills_since(cls, date_cutoff):
        """
        grabs all bills that have had activity since a given date
        """
        return cls.objects.filter(last_action_date__gte=date_cutoff)

    @classmethod
    def new_bills_since(cls, date_cutoff):
        """
        grabs all bills that have been added since a given date
        (bills_since = new_bills_since + updated_bills_since)
        """
        all_bills_since = cls.bills_since(date_cutoff)
        new_bills_since = [b for b in all_bills_since if b.first_action.date >= date_cutoff]
        return new_bills_since


    @classmethod
    def updated_bills_since(cls, date_cutoff):
        """
        grabs all previously existing bills that have had activity since a given date
        (bills_since = new_bills_since + updated_bills_since)
        """
        all_bills_since = cls.bills_since(date_cutoff)
        updated_bills_since = [b for b in all_bills_since if b.first_action.date < date_cutoff]
        return updated_bills_since

    @property
    def unique_related_upcoming_events(self):
        events = [r.agenda_item.event for r in self.related_agenda_items.filter(agenda_item__event__start_time__gte=datetime.now()).all()]
        return list(set(events))


class Organization(models.Model):
    ocd_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    classification = models.CharField(max_length=255, null=True)
    _parent = models.ForeignKey('self', related_name='children', null=True, db_column='parent_id')
    source_url = models.CharField(max_length=255, blank=True)
    slug = models.CharField(max_length=255, unique=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def parent(self):
        return override_relation(self._parent)

    def __str__(self):
        return self.name

    @classmethod
    def committees(cls):
        """
        grabs all organizations (1) classified as a committee & (2) with at least one member
        """
        return cls.objects.filter(classification='committee').order_by('name').filter(memberships__isnull=False).distinct()

    @property
    def recent_activity(self):
        # setting arbitrary max of 300 b/c otherwise page will take forever to load
        return self.actions.order_by('-date', '-_bill__identifier', '-order')[:300] if self.actions.all() else None

    @property
    def recent_events(self):
        # need to look up event participants by name
        events = Event.objects.filter(participants__entity_type='organization').filter(participants__entity_name=self.name).order_by('-start_time').all()
        return events

    @property
    def chairs(self):
        if hasattr(settings, 'COMMITTEE_CHAIR_TITLE'):
            return self.memberships.filter(role=settings.COMMITTEE_CHAIR_TITLE)
        else:
            return None

    @property
    def non_chair_members(self):
        if hasattr(settings, 'COMMITTEE_MEMBER_TITLE'):
            return self.memberships.filter(role=settings.COMMITTEE_MEMBER_TITLE)
        else:
            return None

    @property
    def link_html(self):
        # make link to committee if committee
        if self.classification == 'committee':
            return '<a href="/committee/'+self.slug+'/">'+self.name+'</a>'
        # link to the council members page if its the council
        if self.classification == 'legislature':
            return '<a href="/council-members/">'+self.name+'</a>'
        # just return text if executive
        else:
            return self.name

class Action(models.Model):
    date = models.DateTimeField(default=None)
    classification = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    _organization = models.ForeignKey('Organization', 
                                      related_name='actions', 
                                      null=True, 
                                      db_column='organization_id')

    _bill = models.ForeignKey('Bill', 
                              related_name='actions', 
                              null=True, 
                              db_column='bill_id')

    order = models.IntegerField()
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def bill(self):
        return override_relation(self._bill)

    @property
    def organization(self):
        return override_relation(self._organization)

    @property
    def related_organization(self):
        r = self.related_entities.first()
        if r and r.entity_type=='organization':
            org = Organization.objects.filter(ocd_id=r.organization_ocd_id).first()
            return org
        else:
            return None

    @property 
    def label(self):
        c = self.classification
        
        if c == 'committee-passage': return 'success'
        if c == 'passage': return 'success'
        if c == 'executive-signature': return 'success'
        if c == 'amendment-passage': return 'success'

        if c == 'amendment-introduction': return 'default'
        if c == 'introduction': return 'default'
        if c == 'committee-referral': return 'default'
        if c == 'filing': return 'default'
        if c == 'executive-received': return 'default'

        if c == 'deferred': return 'primary'

        else: return 'default'

    @classmethod
    def actions_on_date(cls, date_match):
        """
        grabs all actions that occurred on a day
        """
        return cls.objects.filter(date__startswith=date_match)

class ActionRelatedEntity(models.Model):
    _action = models.ForeignKey('Action', related_name='related_entities', db_column='action_id', null=True)
    entity_type = models.CharField(max_length=100)
    entity_name = models.CharField(max_length=255)
    organization_ocd_id = models.CharField(max_length=100, blank=True)
    person_ocd_id = models.CharField(max_length=100, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def action(self):
        return override_relation(self._action)

class Post(models.Model):
    ocd_id = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    _organization = models.ForeignKey('Organization', related_name='posts', db_column='organization_id', null=True)
    division_ocd_id = models.CharField(max_length=255)
    shape = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def organization(self):
        return override_relation(self._organization)

    @property
    def current_member(self):
        if self.memberships:
            most_recent_member = self.memberships.order_by('-start_date', '-end_date').first()
            if most_recent_member.end_date:
                return None
            else:
                return most_recent_member
        else:
            return None

class Membership(models.Model):
    _organization = models.ForeignKey('Organization', related_name='memberships', db_column='organization_id', null=True)
    _person = models.ForeignKey('Person', related_name='memberships', db_column='person_id', null=True)
    _post = models.ForeignKey('Post', related_name='memberships', null=True, db_column='post_id')
    label = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(default=None, null=True)
    end_date = models.DateField(default=None, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def organization(self):
        return override_relation(self._organization)
    
    @property
    def person(self):
        return override_relation(self._person)
    
    @property
    def post(self):
        return override_relation(self._post)

class Sponsorship(models.Model):
    _bill = models.ForeignKey('Bill', related_name='sponsorships', db_column='bill_id', null=True)
    _person = models.ForeignKey('Person', related_name='sponsorships', db_column='person_id', null=True)
    classification = models.CharField(max_length=255)
    is_primary = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def bill(self):
        return override_relation(self._bill)
    
    @property
    def person(self):
        return override_relation(self._person)

    def __str__(self):
        return '{0} ({1})'.format(self.bill.identifier, self.person.name)

class Event(models.Model):
    ocd_id = models.CharField(max_length=100, unique=True)
    ocd_created_at = models.DateTimeField(default=None)
    ocd_updated_at = models.DateTimeField(default=None)
    name = models.CharField(max_length=255)
    description = models.TextField()
    classification = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)
    all_day = models.BooleanField(default=False)
    status = models.CharField(max_length=100)
    location_name = models.CharField(max_length=255)
    location_url = models.CharField(max_length=255, blank=True)
    source_url = models.CharField(max_length=255)
    source_note = models.CharField(max_length=255, blank=True)
    slug = models.CharField(max_length=255, unique=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def event_page_url(self):
        return '/event/%s' %self.slug

    @property
    def link_html(self):
        return '<a href="'+self.event_page_url+'/" title="View Event Details">'+self.name+'</a>' 

    @property
    def clean_agenda_items(self):
        agenda_items = self.agenda_items.order_by('order').all()
        agenda_deduped = []
        descriptions_seen = []
        for a in agenda_items:
            if a.description not in descriptions_seen:
                descriptions_seen.append(a.description)
                agenda_deduped.append(a)

        return agenda_deduped

    @classmethod
    def next_city_council_meeting(cls):
        if hasattr(settings, 'CITY_COUNCIL_MEETING_NAME'):
            return cls.objects.filter(name__icontains=settings.CITY_COUNCIL_MEETING_NAME)\
                  .filter(start_time__gt=datetime.now()).order_by('start_time').first()
        else:
            return None

    @classmethod
    def most_recent_past_city_council_meeting(cls):
        if hasattr(settings, 'CITY_COUNCIL_MEETING_NAME'):
            return cls.objects.filter(name__icontains=settings.CITY_COUNCIL_MEETING_NAME)\
                  .filter(start_time__lt=datetime.now()).order_by('-start_time').first()
        else:
            return None

    @classmethod
    def upcoming_committee_meetings(cls):
        return cls.objects.filter(start_time__gt=datetime.now())\
                  .exclude(name='City Council Stated Meeting')\
                  .exclude(name='City Council Stated Meeting ')\
                  .order_by('start_time').all()[:3]

class EventParticipant(models.Model):
    event = models.ForeignKey('Event', related_name='participants')
    note = models.TextField()
    entity_name = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __init__(self, *args, **kwargs):
        super(EventParticipant, self).__init__(*args, **kwargs)
        self.event = override_relation(self.event)

class EventAgendaItem(models.Model):
    event = models.ForeignKey('Event', related_name='agenda_items')
    order = models.IntegerField()
    description = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    
    def __init__(self, *args, **kwargs):
        super(EventAgendaItem, self).__init__(*args, **kwargs)
        self.event = override_relation(self.event)

class AgendaItemBill(models.Model):
    agenda_item = models.ForeignKey('EventAgendaItem', related_name='related_bills')
    bill = models.ForeignKey('Bill', related_name='related_agenda_items')
    note = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __init__(self, *args, **kwargs):
        super(AgendaItemBill, self).__init__(*args, **kwargs)
        self.agenda_item = override_relation(self.agenda_item)
        self.bill = override_relation(self.bill)

class Document(models.Model):
    note = models.TextField()
    url = models.TextField(blank=True)
    full_text = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

class BillDocument(models.Model):
    bill = models.ForeignKey('Bill', related_name='documents')
    document = models.ForeignKey('Document', related_name='bills')
    document_type = models.CharField(max_length=255, choices=bill_document_choices)
    updated_at = models.DateTimeField(auto_now=True)

    def __init__(self, *args, **kwargs):
        super(BillDocument, self).__init__(*args, **kwargs)
        self.bill = override_relation(self.bill)
        self.document = override_relation(self.document)

class EventDocument(models.Model):
    event = models.ForeignKey('Event', related_name='documents')
    document = models.ForeignKey('Document', related_name='events')
    updated_at = models.DateTimeField(auto_now=True)
    
    def __init__(self, *args, **kwargs):
        super(EventDocument, self).__init__(*args, **kwargs)
        self.event = override_relation(self.event)
        self.document = override_relation(self.document)

class LegislativeSession(models.Model):
    identifier = models.CharField(max_length=255)
    jurisdiction_ocd_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)

