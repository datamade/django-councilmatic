import datetime
import os

from django.db import models
from django.contrib.gis.db import models as geo_models
from django.conf import settings
from django.urls import reverse, NoReverseMatch
from django.utils import timezone
from django.db.models import Case, When
from django.db.models.functions import Cast, Now
from django.utils.functional import cached_property
from django.core.files.storage import FileSystemStorage

from proxy_overrides.related import ProxyForeignKey
import opencivicdata.legislative.models
import opencivicdata.core.models


static_storage = FileSystemStorage(location=os.path.join(settings.STATIC_ROOT), base_url='/')

MANUAL_HEADSHOTS = settings.MANUAL_HEADSHOTS if hasattr(settings, 'MANUAL_HEADSHOTS') else {}


class CastToDateTimeMixin:

    @classmethod
    def cast_to_datetime(cls, field):
        """
        Cast a given field from a CharField to a DateTimeField, converting empty
        strings to NULL in the process. Useful for CharFields that store timestamps
        as strings.
        """
        return Cast(
            Case(
                When(**{field: '', 'then': None}),
                default=field,
                output_field=models.CharField()
            ),
            models.DateTimeField()
        )


class Person(opencivicdata.core.models.Person):

    person = models.OneToOneField(opencivicdata.core.models.Person,
                                  on_delete=models.CASCADE,
                                  related_name='councilmatic_person',
                                  parent_link=True)

    headshot = models.FileField(upload_to='images/headshots',
                                storage=static_storage,
                                default='images/headshot_placeholder.png')

    slug = models.SlugField(unique=True)

    def delete(self, **kwargs):
        kwargs['keep_parents'] = kwargs.get('keep_parents', True)
        super().delete(**kwargs)

    def __str__(self):
        return self.name

    @property
    def current_memberships(self):
        return self.memberships.filter(end_date_dt__gt=Now())

    @property
    def latest_council_seat(self):
        m = self.latest_council_membership
        if m and m.post:
            return m.post.label
        return ''

    @property
    def headshot_source(self):
        sources = self.sources.filter(url=self.headshot.url)
        if sources:
            return sources.get().note
        elif self.headshot:
            return settings.CITY_VOCAB['SOURCE']
        else:
            return None

    @property
    def primary_sponsorships(self):
        primary_sponsorships = self.billsponsorship_set.filter(primary=True)\
                                                       .prefetch_related('bill')

        def sponsorship_sort(sponsorship):
            '''
            Sponsorships of bills without recent action dates should appear last.
            '''
            return sponsorship.bill.last_action_date or datetime.datetime(datetime.MINYEAR, 1, 1)

        return sorted((s for s in primary_sponsorships), key=sponsorship_sort, reverse=True)

    @property
    def chair_role_memberships(self):
        if hasattr(settings, 'COMMITTEE_CHAIR_TITLE'):
            return self.current_memberships.filter(role=settings.COMMITTEE_CHAIR_TITLE)
        else:
            return []

    @property
    def member_role_memberships(self):
        if hasattr(settings, 'COMMITTEE_MEMBER_TITLE'):
            return self.current_memberships.filter(role=settings.COMMITTEE_MEMBER_TITLE)
        else:
            return []

    @property
    def latest_council_membership(self):
        filter_kwarg = {'organization__name': settings.OCD_CITY_COUNCIL_NAME}

        city_council_memberships = self.memberships.filter(**filter_kwarg)

        if city_council_memberships.count():
            return city_council_memberships.order_by('-start_date', '-end_date').first()

        return None

    @property
    def current_council_seat(self):
        m = self.latest_council_membership
        if m and m.end_date_dt > timezone.now():
            return m

    @property
    def link_html(self):
        return "<a href='{}'>{}</a>".format(reverse('person', args=[self.slug]), self.name)


class Organization(opencivicdata.core.models.Organization, CastToDateTimeMixin):

    organization = models.OneToOneField(opencivicdata.core.models.Organization,
                                        on_delete=models.CASCADE,
                                        related_name='councilmatic_organization',
                                        parent_link=True)

    slug = models.SlugField(max_length=200, unique=True)

    def delete(self, **kwargs):
        kwargs['keep_parents'] = kwargs.get('keep_parents', True)
        super().delete(**kwargs)

    def __str__(self):
        return self.name

    @classmethod
    def committees(cls):
        """
        grabs all organizations (1) classified as a committee & (2) with at least one member
        """
        return cls.objects\
            .filter(classification='committee')\
            .annotate(memberships_end_date_dt=cls.cast_to_datetime('memberships__end_date'))\
            .filter(memberships_end_date_dt__gte=Now())\
            .distinct()

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
            chairs = self.memberships.filter(role=settings.COMMITTEE_CHAIR_TITLE).filter(end_date_dt__gt=timezone.now()).select_related('person__councilmatic_person')
            for chair in chairs:
                chair.person = chair.person.councilmatic_person
            return chairs
        else:
            return []

    @property
    def non_chair_members(self):
        if hasattr(settings, 'COMMITTEE_MEMBER_TITLE'):
            return self.memberships.filter(role=settings.COMMITTEE_MEMBER_TITLE).filter(end_date_dt__gt=timezone.now())
        else:
            return []

    @property
    def all_members(self):
        return self.memberships.filter(end_date_dt__gt=timezone.now())

    @property
    def vice_chairs(self):
        if hasattr(settings, 'COMMITTEE_VICE_CHAIR_TITLE'):
            return self.memberships.filter(role=settings.COMMITTEE_VICE_CHAIR_TITLE).filter(end_date_dt__gt=timezone.now())
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

    post = models.OneToOneField(opencivicdata.core.models.Post,
                                on_delete=models.CASCADE,
                                related_name='councilmatic_post',
                                parent_link=True)

    organization = ProxyForeignKey(
        Organization,
        related_name='posts',
        help_text="The Organization in which the post is held.",
        on_delete=models.CASCADE,
    )

    shape = geo_models.GeometryField(null=True)

    @cached_property
    def current_member(self):
        membership = self.memberships.filter(end_date_dt__gt=timezone.now())\
                                     .order_by('-end_date', '-start_date')\
                                     .select_related('person__councilmatic_person').first()
        if membership:
            membership.person = membership.person.councilmatic_person
            return membership


class MembershipManager(CastToDateTimeMixin, models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(
            end_date_dt=self.cast_to_datetime('end_date'),
            start_date_dt=self.cast_to_datetime('start_date')
        )


class Membership(opencivicdata.core.models.Membership, CastToDateTimeMixin):
    class Meta:
        proxy = True
        base_manager_name = 'objects'

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


class EventManager(CastToDateTimeMixin, models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(
            start_time=self.cast_to_datetime('start_date')
        )


class Event(opencivicdata.legislative.models.Event):

    event = models.OneToOneField(opencivicdata.legislative.models.Event,
                                 on_delete=models.CASCADE,
                                 related_name='councilmatic_event',
                                 parent_link=True)

    slug = models.SlugField(max_length=200, unique=True)

    def delete(self, **kwargs):
        kwargs['keep_parents'] = kwargs.get('keep_parents', True)
        super().delete(**kwargs)

    objects = EventManager()

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

    @property
    def local_start_time(self):
        return timezone.localtime(self.start_time)


class Bill(opencivicdata.legislative.models.Bill):

    bill = models.OneToOneField(opencivicdata.legislative.models.Bill,
                                on_delete=models.CASCADE,
                                related_name='councilmatic_bill',
                                parent_link=True)

    slug = models.SlugField(unique=True)
    restrict_view = models.BooleanField(default=False)
    last_action_date = models.DateTimeField(blank=True, null=True)

    def delete(self, **kwargs):
        kwargs['keep_parents'] = kwargs.get('keep_parents', True)
        super().delete(**kwargs)

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
    def web_source(self):
        return self.sources.filter(note='web').get()

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

    def get_last_action_date(self):
        '''
        Return the date of the most recent action. If there is no action,
        return the date of the most recent past event for which the bill
        appears on the agenda. Otherwise, return None.
        '''
        current_action = self.current_action

        if current_action:
            return current_action.date_dt

        try:
            last_agenda = Event.objects.filter(start_time__lte=timezone.now(),
                                               agenda__related_entities__bill=self)\
                                       .latest('start_time')
        except Event.DoesNotExist:
            return None

        else:
            return last_agenda.start_time


class BillSponsorship(opencivicdata.legislative.models.BillSponsorship):
    class Meta:
        proxy = True

    bill = ProxyForeignKey(Bill, related_name='sponsorships', on_delete=models.CASCADE)
    organization = ProxyForeignKey(Organization, null=True, on_delete=models.SET_NULL)
    person = ProxyForeignKey(Person, null=True, on_delete=models.SET_NULL)


class BillActionManager(CastToDateTimeMixin, models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(
            date_dt=self.cast_to_datetime('date')
        )


class BillAction(opencivicdata.legislative.models.BillAction):
    class Meta:
        proxy = True

    objects = BillActionManager()

    bill = ProxyForeignKey(Bill,
                           related_name='actions',
                           on_delete=models.CASCADE)

    organization = ProxyForeignKey(Organization,
                                   related_name='actions',
                                   # don't let an org delete wipe out a bunch of bill actions
                                   on_delete=models.PROTECT)

    @property
    def label(self):
        c = self.classification
        if not c:
            return 'default'
        c = c[0]

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

    @cached_property
    def referred_org(self):
        if self.description == 'Referred':
            related_entity = self.related_entities.get()
            if related_entity:
                return related_entity.organization


class BillActionRelatedEntity(opencivicdata.legislative.models.BillActionRelatedEntity):
    class Meta:
        proxy = True

    action = ProxyForeignKey(BillAction,
                             related_name='related_entities',
                             on_delete=models.CASCADE)

    organization = ProxyForeignKey(Organization,
                                   null=True,
                                   on_delete=models.SET_NULL)
