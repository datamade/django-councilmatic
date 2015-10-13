from django.shortcuts import render, redirect
from django.http import Http404
from django.conf import settings
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from .models import Person, Bill, Organization, Action, Event, Post
from haystack.forms import FacetedSearchForm
from datetime import date, timedelta
from itertools import groupby

class CouncilmaticSearchForm(FacetedSearchForm):
    
    def __init__(self, *args, **kwargs):
        self.load_all = True

        super(CouncilmaticSearchForm, self).__init__(*args, **kwargs)

    def no_query_found(self):
        return self.searchqueryset.all()

def city_context(request):
    return {
        'SITE_META': getattr(settings, 'SITE_META', None),
        'CITY_COUNCIL_NAME': getattr(settings, 'CITY_COUNCIL_NAME', None),
        'CITY_NAME': getattr(settings, 'CITY_NAME', None),
        'CITY_NAME_SHORT': getattr(settings, 'CITY_NAME_SHORT', None),
        'SEARCH_PLACEHOLDER_TEXT': getattr(settings,'SEARCH_PLACEHOLDER_TEXT', None),
        'LEGISLATION_TYPE_DESCRIPTIONS': getattr(settings,'LEGISLATION_TYPE_DESCRIPTIONS', None),
        'LEGISTAR_URL': getattr(settings,'LEGISTAR_URL', None),
    }

class IndexView(TemplateView):
     
    template_name = 'councilmatic_core/index.html'
    bill_model = Bill
    event_model = Event

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        
        some_time_ago = date.today() + timedelta(days=-100)
        recent_legislation = self.bill_model.objects\
                                 .exclude(last_action_date=None)\
                                 .filter(last_action_date__gt=some_time_ago)\
                                 .order_by('-last_action_date').all()

        recently_passed = [l for l in recent_legislation \
                               if l.inferred_status == 'Passed' \
                                   and l.bill_type == 'Introduction'][:3]
        
        upcoming_meetings = list(self.event_model.upcoming_committee_meetings())

        return {
            'recent_legislation': recent_legislation,
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
        return Post.objects.filter(organization__ocd_id=settings.OCD_CITY_COUNCIL_ID)

class BillDetailView(DetailView):
    model = Bill
    template_name = 'councilmatic_core/legislation.html'
    context_object_name = 'legislation'
    
    def get_context_data(self, **kwargs):
        context = super(BillDetailView, self).get_context_data(**kwargs)
        
        context['actions'] = self.get_object().actions.all().order_by('-order')
        
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
        context['chairs'] = committee.memberships.filter(role='CHAIRPERSON')
        context['memberships'] = committee.memberships.filter(role='Committee Member')
        
        if getattr(settings, 'COMMITTEE_DESCRIPTIONS', None):
            description = settings.COMMITTEE_DESCRIPTIONS.get(self.get_slug())
            context['committee_description'] = description

        return context

class PersonDetailView(DetailView):
    model = Person
    template_name = 'councilmatic_core/person.html'
    context_object_name = 'person'
    
    def get_context_data(self, **kwargs):
        context = super(PersonDetailView, self).get_context_data(**kwargs)
        
        person = context['person']
        context['sponsorships'] = person.primary_sponsorships.order_by('-bill__last_action_date')

        context['chairs'] = person.memberships.filter(role="CHAIRPERSON")
        context['memberships'] = person.memberships.filter(role="Committee Member")

        return context

def not_found(request):
    return render(request, 'councilmatic_core/404.html')


def events(request, year=None, month=None):

    newest_year = Event.objects.all().order_by('-start_time').first().start_time.year
    oldest_year = Event.objects.all().order_by('start_time').first().start_time.year
    year_range = list(reversed(range(oldest_year, newest_year+1)))
    month_options = [
        ['January', 1],
        ['February',2],
        ['March',3],
        ['April',4],
        ['May',5],
        ['June',6],
        ['July',7],
        ['August',8],
        ['September',9],
        ['October',10],
        ['November',11],
        ['December',12]
    ]

    if not year or not month:
        year = date.today().year
        month = date.today().month

        upcoming_dates = Event.objects.filter(start_time__gt=date.today()).datetimes('start_time', 'day').order_by('start_time')[:50]
        upcoming_events = []
        for d in upcoming_dates:
            if not (upcoming_events and d == upcoming_events[-1][0]):
                events_on_day = Event.objects.filter(start_time__year=d.year).filter(start_time__month=d.month).filter(start_time__day=d.day).order_by('start_time').all()
                upcoming_events.append([d, events_on_day])

        context = {
            'show_upcoming': True,
            'this_month': month,
            'this_year': year,
            'upcoming_events': upcoming_events,
            'year_range': year_range,
            'month_options': month_options,
        }

        return render(request, 'councilmatic_core/events.html', context)
    else:
        year = int(year)
        month = int(month)

        month_dates = Event.objects.filter(start_time__year=year).filter(start_time__month=month).datetimes('start_time', 'day').order_by('start_time')
        month_events = []
        for d in month_dates:
            if not (month_events and d == month_events[-1][0]):
                events_on_day = Event.objects.filter(start_time__year=d.year).filter(start_time__month=d.month).filter(start_time__day=d.day).order_by('start_time').all()
                month_events.append([d, events_on_day])

        context = {
            'show_upcoming': False,
            'this_month': month,
            'this_year': year,
            'first_date': month_dates[0] if month_dates else None,
            'month_events': month_events,
            'year_range': year_range,
            'month_options': month_options,
        }

        return render(request, 'councilmatic_core/events.html', context)

def event_detail(request, slug):

    event = Event.objects.filter(slug=slug).first()

    participants = [ Organization.objects.filter(name=p.entity_name).first() for p in event.participants.all()]
    context = {
        'event': event,
        'participants': participants
    }

    return render(request, 'councilmatic_core/event.html', context)

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                login(request, user)
                return redirect('index')
    else:
        form = AuthenticationForm()

    return render(request, 'core_user/login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('index')
