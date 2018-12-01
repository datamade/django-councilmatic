from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.urls import reverse, NoReverseMatch
from django.utils import timezone
from django.db.models.functions import Cast
from django.utils.text import slugify, Truncator
from django.utils.functional import cached_property

from proxy_overrides.related import ProxyForeignKey

import opencivicdata.legislative.models
import opencivicdata.core.models

if not (hasattr(settings, 'OCD_CITY_COUNCIL_ID') or hasattr(settings, 'OCD_CITY_COUNCIL_NAME')):
    raise ImproperlyConfigured(
        'You must define a OCD_CITY_COUNCIL_ID or OCD_CITY_COUNCIL_NAME in settings.py')

if not hasattr(settings, 'CITY_COUNCIL_NAME'):
    raise ImproperlyConfigured(
        'You must define a CITY_COUNCIL_NAME in settings.py')

MANUAL_HEADSHOTS = settings.MANUAL_HEADSHOTS if hasattr(
    settings, 'MANUAL_HEADSHOTS') else {}

def get_uuid():
    import uuid
    return str(uuid.uuid4())

class Person(opencivicdata.core.models.Person):

    class Meta:
        proxy = True

    def __str__(self):
        return self.name

    @property
    def latest_council_seat(self):
        m = self.latest_council_membership
        if m and m.post:
            return m.post.label
        return ''

    @property
    def is_speaker(self):
        return True if self.memberships.filter(role='Speaker').first() else False

    @property
    def headshot_url(self):
        if self.slug in MANUAL_HEADSHOTS:
            return '/static/images/' + MANUAL_HEADSHOTS[self.slug]['image']
        #elif self.headshot:
        #    return '/static/images/' + self.ocd_id + ".jpg
        else:
            return '/static/images/headshot_placeholder.png'

    @property
    def headshot_source(self):
        if self.slug in MANUAL_HEADSHOTS:
            return MANUAL_HEADSHOTS[self.slug]['source']
        #elif self.headshot:
        #    return settings.CITY_VOCAB['SOURCE']
        else:
            return None

    @property
    def primary_sponsorships(self):
        return self.billsponsorship_set.filter(primary=True)

    @property
    def chair_role_memberships(self):
        if hasattr(settings, 'COMMITTEE_CHAIR_TITLE'):
            return self.memberships.filter(role=settings.COMMITTEE_CHAIR_TITLE).filter(end_date__gt=timezone.now())
        else:
            return []

    @property
    def member_role_memberships(self):
        if hasattr(settings, 'COMMITTEE_MEMBER_TITLE'):
            return self.memberships.filter(role=settings.COMMITTEE_MEMBER_TITLE).filter(end_date__gt=timezone.now())
        else:
            return []

    @property
    def link_html(self):
        
        if self.id and self.slug:
    
            try:
                link_path = reverse('{}:person'.format(settings.APP_NAME), args=(self.slug,))
                
            except NoReverseMatch:
                link_path = reverse('person', args=(self.slug,))
    
            return '<a href="{0}" title="More on {1}">{1}</a>'.format(link_path, self.name)
    
        return self.name

    @property
    def slug(self):
    
        ocd_part = self.id.rsplit('-', 1)[1]
        return '{0}-{1}'.format(slugify(self.name),ocd_part)
    
    @property
    def latest_council_membership(self):
        if hasattr(settings, 'OCD_CITY_COUNCIL_ID'):
            filter_kwarg = {'organization__id': settings.OCD_CITY_COUNCIL_ID}
        else:
            filter_kwarg = {'organization__name': settings.OCD_CITY_COUNCIL_NAME}
    
        city_council_memberships = self.memberships.filter(**filter_kwarg)
    
        if city_council_memberships.count():
            return city_council_memberships.order_by('-start_date', '-end_date').first()
    
        return None
    
    @property
    def current_council_seat(self):
        m = self.latest_council_membership
        if m and m.end_date_dt > timezone.now():
            return m.post.label
        return ''

class Organization(opencivicdata.core.models.Organization):

    class Meta:
        proxy = True

    @property
    def slug(self):

        ocd_part = self.id.rsplit('-', 1)[1]
        return '{0}-{1}'.format(slugify(self.name),ocd_part)

    def __str__(self):
        return self.name

    @classmethod
    def committees(cls):
        """
        grabs all organizations (1) classified as a committee & (2) with at least one member
        """
        return cls.objects.filter(classification='committee').order_by('name').filter(memberships__end_date__gt=timezone.now()).distinct()

    @property
    def recent_activity(self):
        # setting arbitrary max of 300 b/c otherwise page will take forever to
        # load
        return self.actions.order_by('-date', '-bill__identifier', '-order')[:300]

    @property
    def recent_events(self):
        # need to look up event participants by name
        events = Event.objects.filter(participants__entity_type='organization', participants__name=self.name)
        events = events.order_by('-start_date').all()
        return events

    @property
    def upcoming_events(self):
        """
        grabs events in the future
        """
        # need to look up event participants by name
        events = Event.objects\
                      .filter(participants__entity_type='organization', participants__name=self.name)\
                      .filter(start_time__gt=timezone.now())\
                      .order_by('start_time')\
                      .all()
        return events

    @property
    def chairs(self):
        if hasattr(settings, 'COMMITTEE_CHAIR_TITLE'):
            foo = self.memberships.filter(role=settings.COMMITTEE_CHAIR_TITLE).filter(end_date__gt=timezone.now())
            return foo
        else:
            return []

    @property
    def non_chair_members(self):
        if hasattr(settings, 'COMMITTEE_MEMBER_TITLE'):
            return self.memberships.filter(role=settings.COMMITTEE_MEMBER_TITLE).filter(end_date__gt=timezone.now())
        else:
            return []

    @property
    def all_members(self):
        if hasattr(settings, 'COMMITTEE_MEMBER_TITLE'):
            return self.memberships.filter(end_date__gt=timezone.now())
        else:
            return []

    @property
    def vice_chairs(self):
        if hasattr(settings, 'COMMITTEE_VICE_CHAIR_TITLE'):
            return self.memberships.filter(role=settings.COMMITTEE_VICE_CHAIR_TITLE).filter(end_date__gt=timezone.now())
        else:
            return []

    @property
    def link_html(self):
        link_fmt = '<a href="{0}">{1}</a>'

        if self.classification == 'committee':

            try:
                link_path = reverse('{}:committee_detail'.format(settings.APP_NAME), args=(self.slug,))
            except NoReverseMatch:
                link_path = reverse('committee_detail', args=(self.slug,))

            return link_fmt.format(link_path, self.name)

        if self.classification == 'legislature':

            try:
                link_path = reverse('{}:council_members'.format(settings.APP_NAME))
            except NoReverseMatch:
                link_path = reverse('council_members')

            return link_fmt.format(link_path, self.name)

        return self.name

class Post(opencivicdata.core.models.Post):
    class Meta:
        proxy=True

    organization = ProxyForeignKey(
        Organization,
        related_name='posts',
        help_text="The Organization in which the post is held.",
        on_delete=models.CASCADE,
    )        

    @cached_property
    def current_member(self):
        return self.memberships.filter(end_date__gt=timezone.now())\
                               .order_by('-end_date', '-start_date')\
                               .first()


class PostShape(models.Model):
    post = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    shape = models.TextField(blank=True, null=True)

class MembershipManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(end_date_dt=Cast('end_date',
                                                                models.DateTimeField()))\
                                     .annotate(start_date_dt=Cast('start_date', models.DateTimeField()))
                                                       

class Membership(opencivicdata.core.models.Membership):
    class Meta:
        proxy = True

    objects = MembershipManager()

    organization = ProxyForeignKey(
        Organization,
        related_name='memberships',
        # memberships will go away if the org does
        on_delete=models.CASCADE,
        help_text="A link to the Organization in which the Person is a member."
    )
    person = ProxyForeignKey(
        Person,
        related_name='memberships',
        null=True,
        # Membership will just unlink if the person goes away
        on_delete=models.SET_NULL,
        help_text="A link to the Person that is a member of the Organization."
    )        

    post = ProxyForeignKey(
        Post,
        related_name='memberships',
        null=True,
        # Membership will just unlink if the post goes away
        on_delete=models.SET_NULL,
        help_text="	The Post held by the member in the Organization."
    )    

class EventManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(start_time=Cast('start_date',
                                                               models.DateTimeField()))

class Event(opencivicdata.legislative.models.Event):

    class Meta:
        proxy = True

    objects = EventManager()

    @property
    def slug(self):
        truncator = Truncator(self.name)
        ocd_part = self.id.rsplit('-', 1)[1]
        return '{0}-{1}'.format(slugify(truncator.words(5)), ocd_part)
        
    
    @property
    def event_page_url(self):

        try:
            link = reverse('{}:event_detail'.format(settings.APP_NAME), args=(self.slug,))
        except NoReverseMatch:
            link = reverse('event_detail', args=(self.slug,))

        return link

    @property
    def link_html(self):
        return '<a href="{0}" title="View Event Details">{1}</a>'.format(self.event_page_url, self.name)

    @property
    def clean_agenda_items(self):
        agenda_items = self.agenda.order_by('order').all()
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
                              .filter(start_time__gt=timezone.now()).order_by('start_time').first()
        else:
            return None

    @classmethod
    def most_recent_past_city_council_meeting(cls):
        if hasattr(settings, 'CITY_COUNCIL_MEETING_NAME'):
            return cls.objects.filter(name__icontains=settings.CITY_COUNCIL_MEETING_NAME)\
                .filter(start_time__lt=timezone.now()).order_by('-start_time').first()
        else:
            return None

    @classmethod
    def upcoming_committee_meetings(cls):
        return cls.objects.filter(start_time__gt=timezone.now())\
                  .exclude(name__icontains=settings.CITY_COUNCIL_MEETING_NAME)\
                  .order_by('start_time').all()[:3]


    

class Bill(opencivicdata.legislative.models.Bill):
    class Meta:
        proxy=True


    @property
    def slug(self):
        return slugify(self.identifier)

    def __str__(self):
        return self.friendly_name

    @property
    def bill_type(self):
        type = self.extras.get('local_classification')
        if not type:
            type, = self.classification

        return type

    @property
    def full_text(self):
        return self.extras.get('rtf_text')

    @property
    def ocr_full_text(self):
        return self.extras.get('plain_text')

    @property
    def html_text(self):
        return self.extras.get('html_text')

    @property
    def controlling_body(self):
        """
        grabs the organization that's currently 'responsible' for a bill
        """

        if self.current_action:
            related_orgs = self.current_action.related_entities.filter(
                entity_type='organization').all()
            # when a bill is referred from city council
            # to a committee, controlling body is the organization
            # the bill was referred to (a related org)
            if related_orgs:
                controlling_bodies = [rel.organization for rel in related_orgs]
                return controlling_bodies
            # otherwise, the controlling body is usually whatever organization
            # performed the most recent action (this is the case most of the
            # time)
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
    def ordered_actions(self):
        """
        returns all actions ordered by date in descending order
        """
        return self.actions.order_by('-order')

    @property
    def current_action(self):
        """
        grabs the most recent action on a bill
        """
        return self.actions.last()

    @property
    def last_action_date(self):
        return self.current_action.date_dt

    @property
    def first_action(self):
        """
        grabs the first action on a bill
        """
        return self.actions.first() if self.actions.all() else None

    @property
    def date_passed(self):
        return self.actions\
                   .filter(classification='passage')\
                   .last().date_dt

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
        return self.sponsorships.filter(primary=True).first()

    @property
    def pseudo_topics(self):
        """
        returns a list of artificial topics for a bill, from the committees
        that have been involved in the bill's history (the actions)

        this serves as a backup when there isn't data on the real topics,
        so that bill listings can still have some useful tags populated
        """
        if self.actions.all():

            orgs = set([a.organization.name for a in self.actions.all() if
                        (a.organization.name != 'Mayor' and
                         a.organization.name != settings.CITY_COUNCIL_NAME)])

            if not orgs and self.controlling_body and \
                    self.controlling_body[0].name != settings.CITY_COUNCIL_NAME:

                orgs = self.controlling_body

            return list(orgs)
        else:
            return []

    @property
    def topics(self):
        """
        returns a list of topics for a bill

        override this in custom subclass for richer topic logic
        """
        return []

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
        abstract = self.abstracts.first()
        if abstract:
            return abstract
        return self.title

    @property
    def full_text_doc_url(self):
        """
        override this if instead of having full text as string stored in
        full_text, it is a PDF document that you can embed on the page
        """
        return None

    @classmethod
    def bills_since(cls, date_cutoff):
        """
        grabs all bills that have had activity since a given date
        """
        return cls.objects.filter(last_action_date_dt__gte=date_cutoff)

    @classmethod
    def new_bills_since(cls, date_cutoff):
        """
        grabs all bills that have been added since a given date
        (bills_since = new_bills_since + updated_bills_since)
        """
        all_bills_since = cls.bills_since(date_cutoff)
        new_bills_since = [
            b for b in all_bills_since if b.first_action.date >= date_cutoff]
        return new_bills_since

    @classmethod
    def updated_bills_since(cls, date_cutoff):
        """
        grabs all previously existing bills that have had activity since a given date
        (bills_since = new_bills_since + updated_bills_since)
        """
        all_bills_since = cls.bills_since(date_cutoff)
        updated_bills_since = [
            b for b in all_bills_since if b.first_action.date < date_cutoff]
        return updated_bills_since

    @property
    def unique_related_upcoming_events(self):
        events = [r.agenda_item.event for r in self.eventrelatedentity_set.filter(
            agenda_item__event__start_date__gte=timezone.now()).all()]
        return list(set(events))

class BillSponsorship(opencivicdata.legislative.models.BillSponsorship):
    class Meta:
        proxy = True        

    bill = ProxyForeignKey(Bill, related_name='sponsorships', on_delete=models.CASCADE)
    person = ProxyForeignKey(Person, null=True, on_delete=models.SET_NULL)

class BillActionManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(date_dt=Cast('date',
                                                            models.DateTimeField()))

    
class BillAction(opencivicdata.legislative.models.BillAction):
    class Meta:
        proxy = True

    bill = ProxyForeignKey(Bill,
                           related_name='actions',
                           on_delete=models.CASCADE)
    organization = ProxyForeignKey(Organization,
                                   related_name='actions',
                                   # don't let an org delete wipe out a bunch of bill actions
on_delete=models.PROTECT)    
    
    objects = BillActionManager()

    @property
    def label(self):
        c = self.classification[0]

        if c == 'committee-passage':
            return 'success'
        if c == 'passage':
            return 'success'
        if c == 'executive-signature':
            return 'success'
        if c == 'amendment-passage':
            return 'success'

        if c == 'amendment-introduction':
            return 'default'
        if c == 'introduction':
            return 'default'
        if c == 'committee-referral':
            return 'default'
        if c == 'filing':
            return 'default'
        if c == 'executive-received':
            return 'default'

        if c == 'deferred':
            return 'primary'

        else:
            return 'default'
    
    
