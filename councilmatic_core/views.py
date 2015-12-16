from django.shortcuts import render, redirect
from django.http import Http404
from django.conf import settings
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Max, Min
from django.core.cache import cache
from .models import Person, Bill, Organization, Action, Event, Post
from haystack.forms import FacetedSearchForm
from haystack.views import FacetedSearchView
from datetime import date, timedelta, datetime
import itertools
from operator import attrgetter

import pytz
import re

app_timezone = pytz.timezone(settings.TIME_ZONE)

class CouncilmaticFacetedSearchView(FacetedSearchView):

    def extra_context(self):
        extra = super(FacetedSearchView, self).extra_context()
        extra['request'] = self.request
        extra['facets'] = self.results.facet_counts()

        selected_facets = {}
        for val in self.request.GET.getlist("selected_facets"):
            [k,v] = val.split('_exact:',1)
            try:
                selected_facets[k].append(v)
            except KeyError:
                selected_facets[k] = [v]
        extra['selected_facets'] = selected_facets

        return extra

class CouncilmaticSearchForm(FacetedSearchForm):
    
    def __init__(self, *args, **kwargs):
        self.load_all = True

        super(CouncilmaticSearchForm, self).__init__(*args, **kwargs)

    def no_query_found(self):
        return self.searchqueryset.all()

# This is used by a context processor in settings.py to render these variables
# into the context of every page.

def city_context(request):
    return {
        'SITE_META': getattr(settings, 'SITE_META', None),
        'FOOTER_CREDITS': getattr(settings, 'FOOTER_CREDITS', None),
        'CITY_COUNCIL_NAME': getattr(settings, 'CITY_COUNCIL_NAME', None),
        'CITY_NAME': getattr(settings, 'CITY_NAME', None),
        'CITY_NAME_SHORT': getattr(settings, 'CITY_NAME_SHORT', None),
        'SEARCH_PLACEHOLDER_TEXT': getattr(settings,'SEARCH_PLACEHOLDER_TEXT', None),
        'LEGISLATION_TYPE_DESCRIPTIONS': getattr(settings,'LEGISLATION_TYPE_DESCRIPTIONS', None),
        'LEGISTAR_URL': getattr(settings,'LEGISTAR_URL', None),
        'DISQUS_SHORTNAME': getattr(settings, 'DISQUS_SHORTNAME', None)
    }

class IndexView(TemplateView):
     
    template_name = 'councilmatic_core/index.html'
    bill_model = Bill
    event_model = Event

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        
        recently_passed = []
        # go back in time at 10-day intervals til you find 3 passed bills
        for i in range(0,-100, -10):
            begin = date.today() + timedelta(days=i)
            end = date.today() + timedelta(days=i-10)

            leg_in_range = self.bill_model.objects\
                                 .exclude(last_action_date=None)\
                                 .filter(last_action_date__lte=begin)\
                                 .filter(last_action_date__gt=end)\
                                 .order_by('-last_action_date')
            passed_in_range = [l for l in leg_in_range \
                               if l.inferred_status == 'Passed']

            recently_passed.extend(passed_in_range)
            if len(recently_passed) >= 3:
                recently_passed = recently_passed[:3]
                break

        upcoming_meetings = list(self.event_model.upcoming_committee_meetings())

        return {
            'recently_passed': recently_passed,
            'next_council_meeting': self.event_model.next_city_council_meeting(),
            'upcoming_committee_meetings': upcoming_meetings,
        }


class AboutView(TemplateView):
    template_name = 'councilmatic_core/about.html'

class CouncilMembersView(ListView):
    template_name = 'councilmatic_core/council_members.html'
    context_object_name = 'posts'
    
    def get_queryset(self):
        return Organization.objects.get(ocd_id=settings.OCD_CITY_COUNCIL_ID).posts.all()
        # return Post.objects.filter(organization__ocd_id=settings.OCD_CITY_COUNCIL_ID)

class BillDetailView(DetailView):
    model = Bill
    template_name = 'councilmatic_core/legislation.html'
    context_object_name = 'legislation'
    
    def get_context_data(self, **kwargs):
        context = super(BillDetailView, self).get_context_data(**kwargs)
        
        context['actions'] = self.get_object().actions.all().order_by('-order')
        bill = context['legislation']

        seo = {}
        seo.update(settings.SITE_META)
        seo['site_desc'] = bill.listing_description
        seo['title'] = '%s - %s' %(bill.friendly_name, settings.SITE_META['site_name'])
        context['seo'] = seo
        
        return context

class CommitteesView(ListView):
    template_name = 'councilmatic_core/committees.html'
    context_object_name = 'committees'

    def get_queryset(self):
        return Organization.committees().filter(name__startswith='Committee')

class CommitteeDetailView(DetailView):
    model = Organization
    template_name = 'councilmatic_core/committee.html'
    context_object_name = 'committee'
    
    def get_context_data(self, **kwargs):
        context = super(CommitteeDetailView, self).get_context_data(**kwargs)
        
        committee = context['committee']
        context['memberships'] = committee.memberships.filter(role='Committee Member')
        
        if getattr(settings, 'COMMITTEE_DESCRIPTIONS', None):
            description = settings.COMMITTEE_DESCRIPTIONS.get(committee.slug)
            context['committee_description'] = description

        seo = {}
        seo.update(settings.SITE_META)
        if description:
            seo['site_desc'] = description
        else:
            seo['site_desc'] = "See what %s's %s has been up to!" %(settings.CITY_COUNCIL_NAME, committee.name)
        seo['title'] = '%s - %s' %(committee.name, settings.SITE_META['site_name'])
        context['seo'] = seo

        return context

class PersonDetailView(DetailView):
    model = Person
    template_name = 'councilmatic_core/person.html'
    context_object_name = 'person'
    
    def get_context_data(self, **kwargs):
        context = super(PersonDetailView, self).get_context_data(**kwargs)
        
        person = context['person']
        context['sponsored_legislation'] = [s.bill for s in person.primary_sponsorships.order_by('-_bill__last_action_date')[:10]]

        seo = {}
        seo.update(settings.SITE_META)
        if person.council_seat:
            short_name = re.sub(r',.*','', person.name)
            seo['site_desc'] = '%s - %s representative in %s. See what %s has been up to!' %(person.name, person.council_seat, settings.CITY_COUNCIL_NAME, short_name)
        else:
            seo['site_desc'] = 'Details on %s, %s' %(person.name, settings.CITY_COUNCIL_NAME)
        seo['title'] = '%s - %s' %(person.name, settings.SITE_META['site_name'])
        seo['image'] = person.headshot_url
        context['seo'] = seo
        
        return context


class EventsView(ListView):
    template_name = 'councilmatic_core/events.html'

    def get_queryset(self):
        # Realize this is stupid. The reason this exists is so that
        # we can have this be a ListView in the inherited subclasses
        # if needed
        return []

    def get_context_data(self, **kwargs):
        context = super(EventsView, self).get_context_data(**kwargs)
        
        aggregates = Event.objects.aggregate(Min('start_time'), Max('start_time'))
        min_year, max_year = aggregates['start_time__min'].year, aggregates['start_time__max'].year
        context['year_range'] = list(reversed(range(min_year, max_year + 1)))
        
        context['month_options'] = []
        for index in range(1, 13):
            month_name = datetime(date.today().year, index, 1).strftime('%B')
            context['month_options'].append([month_name, index])
        
        context['show_upcoming'] = True
        context['this_month'] = date.today().month
        context['this_year'] = date.today().year
        events_key = 'upcoming_events'

        upcoming_dates = Event.objects.filter(start_time__gt=date.today())
        
        current_year = self.request.GET.get('year')
        current_month = self.request.GET.get('month')
        if current_year and current_month:
            events_key = 'month_events'
            upcoming_dates = Event.objects\
                                  .filter(start_time__year=int(current_year))\
                                  .filter(start_time__month=int(current_month))
            
            context['show_upcoming'] = False
            context['this_month'] = int(current_month)
            context['this_year'] = int(current_year)
        
        upcoming_dates = upcoming_dates.order_by('start_time')
        
        day_grouper = lambda x: (x.start_time.year, x.start_time.month, x.start_time.day)
        context[events_key] = []
        
        for event_date, events in itertools.groupby(upcoming_dates, key=day_grouper):
            events = sorted(events, key=attrgetter('start_time'))
            context[events_key].append([date(*event_date), events])
        
        return context

class EventDetailView(DetailView):
    template_name = 'councilmatic_core/event.html'
    model = Event
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super(EventDetailView, self).get_context_data(**kwargs)
        event = context['event']

        participants = [p.entity_name for p in event.participants.all()]
        context['participants'] = Organization.objects.filter(name__in=participants)

        seo = {}
        seo.update(settings.SITE_META)
        seo['site_desc'] = 'Public city council event on %s/%s/%s - view event participants & agenda items' %(event.start_time.month, event.start_time.day, event.start_time.year)
        seo['title'] = '%s Event - %s' %(event.name, settings.SITE_META['site_name'])
        context['seo'] = seo
        
        return context

def not_found(request):
    return render(request, 'councilmatic_core/404.html')

def flush(request, flush_key):

    try:
        if flush_key == settings.FLUSH_KEY:
            cache.clear()
    except AttributeError:
        print("\n\n** NOTE: to use flush-cache, set FLUSH_KEY in settings_local.py **\n\n")

    return redirect('index')
