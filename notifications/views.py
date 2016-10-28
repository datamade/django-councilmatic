from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.template.loader import get_template
from django.template import Context
from django.db.models import Q
from django.db import IntegrityError

from councilmatic_core.models import Bill, Organization, Person, Event
from notifications.models import PersonSubscription, BillActionSubscription, CommitteeActionSubscription, CommitteeEventSubscription, BillSearchSubscription, EventsSubscription
from django.core.exceptions import ObjectDoesNotExist
#from councilmatic.settings import * # XXX seems like I should definitely not be importing "from councilmatic. " over in django-councilmatic

import rq

from redis import Redis

import django_rq
import json
import datetime
import pytz
import sys

from django.core.mail import send_mail
from django.core.cache import cache

from django.forms import EmailField
from django.core.mail import EmailMessage

from django.contrib.auth.models import User # XXX TODO: migrate to custom User model https://docs.djangoproject.com/en/1.9/topics/auth/customizing/ http://blog.mathandpencil.com/replacing-django-custom-user-models-in-an-existing-application/ https://www.caktusgroup.com/blog/2013/08/07/migrating-custom-user-model-django/

from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _

app_timezone = pytz.timezone(settings.TIME_ZONE)

# These are the main two redis queues: notifications_queues is woken up when a loaddata run completes;
# notifications_emails_queue is woken up when an email should be sent to a notification subscriber.
# XXX put these global variables in some more appropriate/official place such as notifications/__init__.py ?

notifications_queue= django_rq.get_queue('notifications')
notification_emails_queue= django_rq.get_queue('notification_emails')

class CouncilmaticUserCreationForm(UserCreationForm):
    email = EmailField(label="Email address", required=True,
        help_text="Required.")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False) # this should set the password
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

def notifications_signup(request):
    form = None
    if request.method == 'POST':
        form = CouncilmaticUserCreationForm(data=request.POST)
        if form.is_valid():
            try:
                form.save()
                return HttpResponseRedirect(reverse('index')) # XXX should either display or redirect to content saying to check your email
            except IntegrityError:
                response = HttpResponse('Not able to save form.')
                response.status_code = 500
                return response
        else:
            return render(request, 'notifications_signup.html', {'form': form}, status=500)
    if not form:
        form = CouncilmaticUserCreationForm()
    return render(request, 'notifications_signup.html', {'form': form})

def notifications_login(request):
    print ("notifications_login()")
    form = None
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            try:
                user = form.get_user()
                login(request, user)
                return HttpResponseRedirect(reverse('index'))
            except IntegrityError:
                response = HttpResponse('Not able to find or login user.')
                response.status_code = 500
                return response
        else:
            return render(request, 'notifications_login.html', {'form': form}, status=500)
    if not form:
        form = AuthenticationForm()
    return render(request, 'notifications_login.html', {'form': form})

def notifications_logout(request):
    logout(request)
    return HttpResponseRedirect('/')

@login_required(login_url='/login/')
def notifications_account_settings(request):
    return HttpResponse('notifications_account_settings')

class SubscriptionsManageView(LoginRequiredMixin, TemplateView):
    template_name = 'subscriptions_manage.html'

    def get_context_data(self, *args, **kwargs):
        context = super(SubscriptionsManageView, self).get_context_data(*args, **kwargs)

        context['person_subscriptions'] = self.request.user.personsubscriptions.all()
        context['committee_action_subscriptions'] = self.request.user.committeeactionsubscriptions.all()
        context['committee_event_subscriptions'] = self.request.user.committeeeventsubscriptions.all()
        context['bill_search_subscriptions'] = self.request.user.billsearchsubscriptions.all()
        context['bill_action_subscriptions'] = self.request.user.billactionsubscriptions.all()
        context['events_subscriptions'] = self.request.user.eventssubscriptions.all()

        return context

@csrf_exempt
@login_required(login_url='/login/')
def bill_subscribe(request, slug):
    bill = Bill.objects.get(slug=slug)
    (bill_action_subscription, created) = BillActionSubscription.objects.get_or_create(user=request.user, bill=bill)
    print ("bill_action_subscription is ", bill_action_subscription)
    print("bill_subscribe(): deleting cache")
    print("cache.get('subscriptions_manage') is ",cache.get('subscriptions_manage'))
    cache.delete('subscriptions_manage')

    return HttpResponse('Subscribed to bill %s.' % str(bill))

@csrf_exempt
@login_required(login_url='/login/')
def bill_unsubscribe(request, slug):
    bill = Bill.objects.get(slug=slug)

    try:
        bill_action_subscription = BillActionSubscription.objects.get(user=request.user, bill=bill)
    except ObjectDoesNotExist:
        response = HttpResponse('This bill subscription does not exist.')
        response.status_code = 500
        return response

    bill_action_subscription.delete()

    return HttpResponse('Unsubscribed from bill %s.' % str(bill))

@csrf_exempt
@login_required(login_url='/login/')
def person_subscribe(request, slug):
    person = Person.objects.get(slug=slug)

    (person_subscription, created) = PersonSubscription.objects.get_or_create(user=request.user, person=person)

    return HttpResponse('Subscribed to person %s.' % str(person))

@csrf_exempt
@login_required(login_url='/login/')
def person_unsubscribe(request, slug):
    person = Person.objects.get(slug=slug)

    try:
        person_subscription = PersonSubscription.objects.get(user=request.user, person=person)
    except ObjectDoesNotExist:
        response = HttpResponse('This person subscription does not exist.')
        response.status_code = 500
        return response

    person_subscription.delete()

    return HttpResponse('Unsubscribed from person %s.' % str(person))

@csrf_exempt
@login_required(login_url='/login/')
def committee_events_subscribe(request, slug):
    committee = Organization.objects.get(slug=slug)
    (committee_events_subscription, created) = CommitteeEventSubscription.objects.get_or_create(user=request.user, committee=committee)

    return HttpResponse('Subscribed to events of %s.' % str(committee))

@csrf_exempt
@login_required(login_url='/login/')
def committee_events_unsubscribe(request, slug):
    committee = Organization.objects.get(slug=slug)
    try:
        committee_events_subscription = CommitteeEventSubscription.objects.get(user=request.user, committee=committee)
    except ObjectDoesNotExist:
        response = HttpResponse('This committee event subscription does not exist.')
        response.status_code = 500
        return response

    committee_events_subscription.delete()
    return HttpResponse('Unsubscribed from events of %s.' % str(committee))

@csrf_exempt
@login_required(login_url='/login/')
def committee_actions_subscribe(request, slug):
    committee = Organization.objects.get(slug=slug)
    (committee_actions_subscription, created) = CommitteeActionSubscription.objects.get_or_create(user=request.user, committee=committee)

    return HttpResponse('Subscribed to actions of %s.' % str(committee))

@csrf_exempt
@login_required(login_url='/login/')
def committee_actions_unsubscribe(request, slug):
    committee = Organization.objects.get(slug=slug)

    try:
        committee_actions_subscription = CommitteeActionSubscription.objects.get(user=request.user, committee=committee)
    except ObjectDoesNotExist:
        response = HttpResponse('This committee action subscription does not exist.')
        response.status_code = 500
        return response

    committee_actions_subscription.delete()

    return HttpResponse('Unsubscribed from actions of %s.' % str(committee))

@csrf_exempt
@login_required(login_url='/login/')
def search_subscribe(request):
    q = request.POST.get('query')
    selected_facets = request.POST.get('selected_facets')
    dict_selected_facets = json.loads(selected_facets)
    (bss, created) = BillSearchSubscription.objects.get_or_create(user=request.user, search_term=q, search_facets = dict_selected_facets)

    return HttpResponse('Subscribed to search for: %s.' % q)

@csrf_exempt
@login_required(login_url='/login/')
def search_unsubscribe(request):
    q = request.POST.get('query')
    selected_facets = request.POST.get('selected_facets')
    selected_facets_json = json.loads(selected_facets)

    try:
        bss = BillSearchSubscription.objects.get(user=request.user,search_term__exact=q, search_facets__exact=selected_facets_json)
    except ObjectDoesNotExist:
        response = HttpResponse('This search subscription does not exist.')
        response.status_code = 500
        return response

    bss.delete()
    return HttpResponse('Unsubscribed from search for: %s.' % q)

@csrf_exempt
@login_required(login_url='/login/')
def search_check_subscription(request):
    q = request.POST.get('query')
    selected_facets = request.POST.get('selected_facets')
    dict_selected_facets = json.loads(selected_facets)

    try:
        bss = BillSearchSubscription.objects.get(user=request.user, search_term__exact=q, search_facets__exact = dict_selected_facets)
    except ObjectDoesNotExist:
        response = HttpResponse('This bill search subscription does not exist.')
        response.status_code = 500
        return response

    return HttpResponse('true')

# search_unsubscribe just takes an ID because it's easier to do this than to marshal dictionaries of search facets around as JSON.
# actually don't do this
#@csrf_exempt
#@login_required(login_url='/login/')
#def search_unsubscribe(request):
#    try:
#        # Make sure that the user in question is the owner of this search subscription by also looking up user=request.user
#        bss = BillSearchSubscription.objects.get(user=request.user, id=search_subscription_id)
#    except ObjectDoesNotExist as e:
#        print ("error", e)     # XXX handle exceptions
#    bss.delete()
#    return HttpResponse('unsubscribe()d')

@csrf_exempt
@login_required(login_url='/login/')
def events_subscribe(request):
    (events_subscription, created) = EventsSubscription.objects.get_or_create(user=request.user)

    return HttpResponse('%s unsubscribed from all events.' % request.user)

@csrf_exempt
@login_required(login_url='/login/')
def events_unsubscribe(request):
    try:
        events_subscription = EventsSubscription.objects.get(user=request.user)
    except ObjectDoesNotExist:
        response = HttpResponse('This event subscription does not exist.')
        response.status_code = 500
        return response

    events_subscription.delete()

    return HttpResponse('%s unsubscribed from all events.' % str(request.user))

# The function worker_handle_notification_email() is invoked when the 'notifications_emails' queue (notification_emails_queue)
# is woken up.
def worker_handle_notification_email(email_recipient_name, email_address, email_subject, email_body):
    print("worker_handle_notification_email(): email_address=", email_address, "email_body=", email_body)
    #print("type(email_body)=", type(email_body))
    email_body = json.loads(email_body)
    #print(email_body)
    #print ("sending mail!!")

    email = EmailMessage(
        email_subject,
        email_body,
        email_address,
        [email_address],
        [],
        #reply_to=['another@example.com'],
        #headers={'Message-ID': 'foo'},
    )

    email.content_subtype = "html"
    email.send()



def handle_person_subscriptions(user, update_since, updated_orgs_ids, updated_people_ids, created_bills_ids, updated_bills_ids, created_events_ids, updated_events_ids):
    person_updates = [] # list of bills sponsored by a person since subscriptions' last_datetime_updated
    # For person updates, we want to hear about any new sponsorships... so look for bills where the most recent date is
    # also one with an Introduction.
    person_subscriptions = PersonSubscription.objects.filter(user=user)
    # find all bills who have this person as a sponsor.
    for p_subscription in person_subscriptions:
        p = p_subscription.person
        #bills=Bill.objects.filter(id__in=updated_bills_ids, sponsorships___person__id = p.id)
        bills=Bill.objects.filter(id__in=created_bills_ids, sponsorships___person__id = p.id)
        for bill in bills:
            actions = bill.actions.all()
            # get the most recent date of all actions
            most_recent_date = max([a.date for a in actions])
            print ("most_recent_date = ", most_recent_date)
            if (most_recent_date < update_since):
                # we can ignore this one as the most recent action date is before our period of updating, therefore there could
                # not have been an introduction in the most recent update
                print ("most_recent_date (", most_recent_date, ") < update_since(", update_since, ")")
                continue
            # given this, did any introductions occur on this date?
            for a in actions:
                if (a.date == most_recent_date and a.classification == 'introduction'):
                    # Found bill with introduction on most recent date, so *probably* a new bill (but could still be an updated
                    # bill with no progress since the introduction date).
                    # XXX: We may be able to look at ocd_created_at vs. ocd_updated_at to disambiguate the above..?
                    print ("found a recent introduction, and for bill id ", bill.id, " we have bill.ocd_created_at=", bill.ocd_created_at, "and bill.ocd_updated_at=", bill.ocd_updated_at)
                    person_updates.append((p, bill))
                    break
    return person_updates

def handle_committee_action_subscriptions(user, update_since, created_bills_ids, updated_bills_ids, created_events_ids, updated_events_ids):
    committee_actions_subscriptions = CommitteeActionSubscription.objects.filter(user=user)
    all_bills_ids = created_bills_ids + updated_bills_ids

    committee_action_updates = [] # list of actions taken by a committee since subscriptions' last_datetime_updated

    for ca_subscription in committee_actions_subscriptions:
        c = ca_subscription.committee
        bills=Bill.objects.filter(
            Q(bill_id__in=all_bills_ids),
            Q(actions__organization = c) | Q(actions__related_organization = c))
        # given this, did any actions with this committee occur on the most recent date?
        for bill in bills:
            actions = bill.actions.all()
            # get the most recent date of all actions
            most_recent_date = max([a.date for a in actions])
            for a in actions:
                if (a.date == most_recent_date and (a.organization == c or a.related_organization == c)):
                    # Found action with this organization on most recent date, so *probably* a new action related to this org
                    # (but could still be an updated bill with no progress since the last action date)
                    # XXX: We may be able to look at ocd_created_at vs. ocd_updated_at to disambiguate the above!
                    print ("found a recent bill action, and for bill id ", bill.id, " we have bill.ocd_created_at=", bill.ocd_created_at, "and bill.ocd_updated_at=", bill.ocd_updated_at)
                    committee_action_updates.append((c, bill, a))
                    break
    return committee_action_updates

def handle_committee_event_subscriptions(user, update_since, created_bills_ids, updated_bills_ids, created_events_ids, updated_events_ids):
    committee_event_subscriptions = CommitteeEventSubscription.objects.filter(user=user)
    #all_events_ids = created_events_ids + updated_events_ids

    person_updates = [] # list of bills sponsored by a person since subscriptions' last_datetime_updated
    committee_action_updates = [] # list of actions taken by a committee since subscriptions' last_datetime_updated
    committee_event_updates = [] # list of events taken by a committee since subscriptions' last_datetime_updated
    bill_search_updates = [] # list of new bills now showing up on a search since subscriptions' last_datetime_updated
    bill_action_updates = [] # list of actions taken on a bill since subscriptions' last_datetime_updated
    events_updates = [] # list of events since subscriptions' last_datetime_updated


    for ce_subscription in committee_event_subscriptions:
        c = ce_subscription.committee
        #events = Event.objects.filter(participants__entity_type='organization', participants__entity_name=self.name)

        created_events = Event.objects.filter(
            Q(id__in=created_events_ids),
            Q(participants__entity_type='organization') | Q(participants__entity_name=c.name)).order_by('-start_time')
        for event in created_events:
            committee_event_updates.append((c, event))

        updated_events = Event.objects.filter(
            Q(id__in=updated_events_ids),
            Q(participants__entity_type='organization') | Q(participants__entity_name=c.name)).order_by('-start_time')
        for event in updated_events:
            committee_event_updates.append((c, event)) #XXX for now, conflate created and updated events
    return committee_event_updates


def handle_bill_search_subscriptions(user, update_since, created_bills_ids, updated_bills_ids, created_events_ids, updated_events_ids):
    billsearch_subscriptions = BillSearchSubscription.objects.filter(user=user)
    person_updates = [] # list of bills sponsored by a person since subscriptions' last_datetime_updated
    committee_action_updates = [] # list of actions taken by a committee since subscriptions' last_datetime_updated
    committee_event_updates = [] # list of events taken by a committee since subscriptions' last_datetime_updated
    bill_search_updates = [] # list of new bills now showing up on a search since subscriptions' last_datetime_updated
    bill_action_updates = [] # list of actions taken on a bill since subscriptions' last_datetime_updated
    events_updates = [] # list of events since subscriptions' last_datetime_updated
    # XXX It's unclear how to proceed here but perhaps evz can weigh in on what the search actually searches,
    # XXX and whether we can simulate that in Python or whether it makes more sense to interact directly with
    # XXX the solr interface on the imported stuff.
    # XXX
    # XXX However, the problem is that with the current cron system, the indexes are not updated immediately
    # XXX with the new data.
    print ("NOT doing bill search subscriptions")

    return bill_search_updates


def handle_bill_action_subscriptions(user, update_since, created_bills_ids, updated_bills_ids, created_events_ids, updated_events_ids):
    print("doing bill action subscriptions for user" , user.username)

    bill_action_updates = []
    # 1) Get all the bills in updated_bills_ids for which we are subscribed.
    # 2) For each of those bills, figure out if some action has occurred or will occur after the last time we updated the subscription (can this happen?)
    ba_subscriptions = BillActionSubscription.objects.filter(bill_id__in=updated_bills_ids, user=user).order_by('bill_id__slug')
    #print ("ba_subscriptions=",ba_subscriptions)
    for ba_subscription in ba_subscriptions:
        b = ba_subscription.bill
        # Look for recent actions which are more recent than the last time we updated
        actions = b.actions.order_by('-date')
        for a in actions:
            if (a.date < ba_subscription.last_datetime_updated):
                pass
            else:
                bill_action_updates.append((b, a)) # add a (Bill, Action) tuple to the list
    return bill_action_updates


def handle_events_subscriptions(user, update_since, created_bills_ids, updated_bills_ids, created_events_ids, updated_events_ids):
    event_updates = []
    events_subscriptions = EventsSubscription.objects.filter(user=user)

    # Basically just return all new events if this is what we are subscribed to.
    # XXX: Whether we include or differentiate updated events will depend on how often updated events actually occur in practice with daily updates.
    all_events_ids = created_events_ids + updated_events_ids
    events = Event.objects.filter(
        Q(id__in=all_events_ids)).order_by('-start_time')
    for event in events:
        event_updates.append(event) #XXX for now, conflate created and updated events
    return event_updates



# This function handles notifications from the queue that includes
# a list of recently updated orgs,people,bills,events
def worker_handle_notification_loaddata(update_since, updated_orgs_ids, updated_people_ids, created_bills_ids, updated_bills_ids, created_events_ids, updated_events_ids):
    # check each user's subscriptions and send off emails
    #print ("worker_handle_notification_loaddata()")
    #print (update_since) # XXX maybe don't need this, because we can just look at the datetimes of the bills/actions/etc.?
    #print (updated_orgs_ids)
    #print (updated_people_ids)
    #print (updated_bills_ids)
    #print (updated_events_ids)

    person_updates = [] # list of bills sponsored by a person since subscriptions' last_datetime_updated
    committee_action_updates = [] # list of actions taken by a committee since subscriptions' last_datetime_updated
    committee_event_updates = [] # list of events taken by a committee since subscriptions' last_datetime_updated
    bill_search_updates = [] # list of new bills now showing up on a search since subscriptions' last_datetime_updated
    bill_action_updates = [] # list of actions taken on a bill since subscriptions' last_datetime_updated
    events_updates = [] # list of events since subscriptions' last_datetime_updated

    # Get all users with some subscriptions.
    users = User.objects.all()
    for user in users:
        # Handle 1) person updates, 2) committee action updates, 3) committee event updates, 4) bill search updates, 5) all event updates
        person_updates = handle_person_subscriptions(user, update_since, updated_orgs_ids, updated_people_ids, created_bills_ids, updated_bills_ids, created_events_ids, updated_events_ids)
        committee_action_updates = handle_committee_action_subscriptions(user, update_since, created_bills_ids, updated_bills_ids, created_events_ids, updated_events_ids)
        committee_event_updates = handle_committee_event_subscriptions(user, update_since, created_bills_ids, updated_bills_ids, created_events_ids, updated_events_ids)
        bill_search_updates = handle_bill_search_subscriptions(user, update_since, created_bills_ids, updated_bills_ids, created_events_ids, updated_events_ids)
        bill_action_updates = handle_bill_action_subscriptions(user, update_since, created_bills_ids, updated_bills_ids, created_events_ids, updated_events_ids)
        events_updates = handle_events_subscriptions(user, update_since, created_bills_ids, updated_bills_ids, created_events_ids, updated_events_ids)

        print ("calling worker_send_email for user ", user.username," with ", len(committee_action_updates), len(committee_event_updates), len(bill_search_updates), len(bill_action_updates), len(events_updates))
        worker_send_email(user, person_updates, committee_action_updates, committee_event_updates, bill_search_updates, bill_action_updates, events_updates)

# Sends a templated email based on the updates, similar to the 'Manage Subscriptions' page
def worker_send_email(user, person_updates, committee_action_updates, committee_event_updates, bill_search_updates, bill_action_updates, events_updates):
    ctx = {
        'person_updates': person_updates,
        'committee_action_updates': committee_action_updates,
        'committee_event_updates': committee_event_updates,
        'bill_search_updates': bill_search_updates,
        'bill_action_updates': bill_action_updates,
        'events_updates': events_updates
    }
    message = get_template('notifications_email.html').render(ctx)

    notification_emails_queue = django_rq.get_queue('notification_emails')
    notification_emails_queue.enqueue(worker_handle_notification_email,
                                      email_recipient_name= json.dumps("%s %s" % (user.first_name, user.last_name)),
                                      email_address=json.dumps(user.email), # XXX is this doing the right thing?
                                      email_subject=json.dumps("Councilmatic notification"),
                                      email_body=json.dumps(message))

# The function notification_loaddata is is posted to by management/loaddata.py
@csrf_exempt
def notification_loaddata(request):
    if request.method != 'POST':
        print("ERROR: notifications/views.py:notification_loaddata() called without POST")

    update_since = json.loads(request.POST.get('update_since'))
    update_since_dt = datetime.datetime.strptime(update_since, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=app_timezone) # XXX is this the right time/place to unmarshal this datetime?
    updated_orgs_ids = json.loads(request.POST.get('updated_orgs_ids'))
    updated_people_ids = json.loads(request.POST.get('updated_people_ids'))
    created_bills_ids = json.loads(request.POST.get('created_bills_ids'))
    updated_bills_ids = json.loads(request.POST.get('updated_bills_ids'))
    created_events_ids = json.loads(request.POST.get('created_events_ids'))
    updated_events_ids = json.loads(request.POST.get('updated_events_ids'))

    print('update_since_dt=', update_since_dt)
    print('updated_orgs_ids=', updated_orgs_ids)
    print('updated_people_ids=', updated_people_ids)
    print('created_bills_ids=', created_bills_ids)
    print('updated_bills_ids=', updated_bills_ids)
    print('created_events_ids=', created_events_ids)
    print('updated_events_ids=', updated_events_ids)

    print("notifications/views.py:new OCD data detected by loaddata.py: %d orgs, %d people, %d created bills, %d updated bills, %d events" % (len(updated_orgs_ids), len(updated_people_ids), len(created_bills_ids), len(updated_bills_ids), len(updated_events_ids)))

    # now let Redis know
    # According to http://python-rq.org/docs/ , uses pickle
    notifications_queue = django_rq.get_queue('notifications')
    notifications_queue.enqueue(worker_handle_notification_loaddata,
                                update_since=update_since_dt,
                                updated_orgs_ids = updated_orgs_ids,
                                updated_people_ids = updated_people_ids,
                                created_bills_ids = created_bills_ids,
                                updated_bills_ids = updated_bills_ids,
                                created_events_ids = created_events_ids,
                                updated_events_ids = updated_events_ids)

    return HttpResponse('ok')


