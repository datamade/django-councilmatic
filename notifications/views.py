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

from councilmatic_core.models import Bill, Organization, Person
from notifications.models import PersonSubscription, BillActionSubscription, CommitteeActionSubscription, CommitteeEventSubscription, BillSearchSubscription
from django.core.exceptions import ObjectDoesNotExist
#from councilmatic.settings import * # XXX seems like I should definitely not be importing "from councilmatic. " over in django-councilmatic

import rq

from redis import Redis

import django_rq
import json

from django.core.mail import send_mail
from django.core.cache import cache

from django.forms import EmailField
from django.core.mail import EmailMessage

from django.contrib.auth.models import User # XXX TODO: migrate to custom User model https://docs.djangoproject.com/en/1.9/topics/auth/customizing/ http://blog.mathandpencil.com/replacing-django-custom-user-models-in-an-existing-application/ https://www.caktusgroup.com/blog/2013/08/07/migrating-custom-user-model-django/ 

from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _

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
        user = super(UserCreationForm, self).save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

def notifications_signup(request):
    form = None
    if request.method == 'POST':
        print("notifications_login(): POST", request.POST)
        form = CouncilmaticUserCreationForm(data=request.POST)
        if form.is_valid():
            print ("got to form in notifications_signup()")
            form.save() # make a new user. XXX handle errors? Also: XXX: how to auto-login user?
            return HttpResponseRedirect(reverse('index'))             # XXX should either display or redirect to content saying to check your email
        else:
            print("signup form not valid") # XXX handle errors
            pass
    if not form:
        form = CouncilmaticUserCreationForm()
    return render(request, 'notifications_signup.html', {'form': form})

def notifications_login(request):
    print ("notifications_login()")
    form = None
    if request.method == 'POST':
        print("notifications_login(): POST", request.POST)
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            print ("form is valid")
            user = form.get_user()
            if user is not None:
                login(request, user)
                return HttpResponseRedirect(reverse('index'))
        else:
            print ("form is NOT valid, form.errors=", form.errors)
    print ("rendering forms")
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
        print ("SubscriptionsManageView: DOIN IT")
        context = super(SubscriptionsManageView, self).get_context_data(*args, **kwargs)
        
        context['person_subscriptions'] = self.request.user.personsubscriptions.all()
        context['committee_action_subscriptions'] = self.request.user.committeeactionsubscriptions.all()
        context['committee_event_subscriptions'] = self.request.user.committeeeventsubscriptions.all()
        context['bill_search_subscriptions'] = self.request.user.billsearchsubscriptions.all()
        context['bill_action_subscriptions'] = self.request.user.billactionsubscriptions.all()

        # XXX not implemented yet
        #context['events_subscriptions'] = self.request.user.personsubscriptions.all()
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
    return HttpResponse('subscribed to bill %s ' % str(bill))

@csrf_exempt
@login_required(login_url='/login/')
def bill_unsubscribe(request, slug):
    bill = Bill.objects.get(slug=slug)
    bill_action_subscription = BillActionSubscription.objects.get(user=request.user, bill=bill)
    bill_action_subscription.delete() # XXX: handle exceptions
    return HttpResponse('bill_unsubscribe')

@csrf_exempt
@login_required(login_url='/login/')
def person_subscribe(request, slug):
    # using the model PersonSubscription using the current user and the Person defined by slug
    person = Person.objects.get(slug=slug)
    (person_subscription, created) = PersonSubscription.objects.get_or_create(user=request.user, person=person)

    return HttpResponse('person_subscribe()d')

@csrf_exempt
@login_required(login_url='/login/')
def person_unsubscribe(request, slug):
    person = Person.objects.get(slug=slug)
    person_subscription = PersonSubscription.objects.get(user=request.user, person=person)
    person_subscription.delete() # XXX handle exceptions
    return HttpResponse('person_unsubscribe()d')

@csrf_exempt
@login_required(login_url='/login/')
def committee_events_subscribe(request, slug):
    committee = Organization.objects.get(slug=slug)
    (committee_events_subscription, created) = CommitteeEventSubscription.objects.get_or_create(user=request.user, committee=committee)

    return HttpResponse('person subscribe()d to committee event')

@csrf_exempt
@login_required(login_url='/login/')
def committee_events_unsubscribe(request, slug):
    committee = Organization.objects.get(slug=slug)
    committee_events_subscription = CommitteeEventSubscription.objects.get(user=request.user, committee=committee)
    committee_events_subscription.delete() # XXX handle exceptions
    return HttpResponse('unsubscribe()d')

@csrf_exempt
@login_required(login_url='/login/')
def committee_actions_subscribe(request, slug):
    committee = Organization.objects.get(slug=slug)
    (committee_actions_subscription, created) = CommitteeActionSubscription.objects.get_or_create(user=request.user, committee=committee) # XXX handle exceptions

    return HttpResponse('person subscribe()d to committee event')

@csrf_exempt
@login_required(login_url='/login/')
def committee_actions_unsubscribe(request, slug):
    committee = Organization.objects.get(slug=slug)
    committee_actions_subscription = CommitteeActionSubscription.objects.get(user=request.user, committee=committee) # XXX handle exceptions
    committee_actions_subscription.delete() # XXX handle exceptions
    return HttpResponse('unsubscribe()d')

@csrf_exempt
@login_required(login_url='/login/')
def search_subscribe(request):
    q = request.POST.get('query')
    selected_facets = request.POST.get('selected_facets')
    dict_selected_facets = json.loads(selected_facets)
    (bss, created) = BillSearchSubscription.objects.get_or_create(user=request.user, search_term=q, search_facets = dict_selected_facets) # XXX handle exceptions
    return HttpResponse('ok')

@csrf_exempt
@login_required(login_url='/login/')
def search_unsubscribe_old(request):
    q = request.POST.get('query')
    selected_facets = request.POST.get('selected_facets')
    #print("q=",q, "selected_facets=", selected_facets, type(selected_facets))
    selected_facets_json = json.loads(selected_facets)
    bss=None
    try:
        bss = BillSearchSubscription.objects.get(user=request.user,search_facets=selected_facets_json)
    except ObjectDoesNotExist as e:
        print ("error", e)     # XXX handle exceptions
    bss.delete() 
    return HttpResponse('unsubscribe()d')

# search_unsubscribe just takes an ID because it's easier to do this than to marshal dictionaries of search facets around as JSON.
@csrf_exempt
@login_required(login_url='/login/')
def search_unsubscribe(request, search_subscription_id):
    try:
        # Make sure that the user in question is the owner of this search subscription by also looking up user=request.user
        bss = BillSearchSubscription.objects.get(user=request.user, id=search_subscription_id)    
    except ObjectDoesNotExist as e:
        print ("error", e)     # XXX handle exceptions
    bss.delete()
    return HttpResponse('unsubscribe()d')

@csrf_exempt
@login_required(login_url='/login/')
def events_subscribe(request, slug):
    (events_subscription, created) = EventsSubscription.objects.get_or_create(user=request.user) # XXX handle exceptions
    return HttpResponse('person subscribe()d to all events')

@csrf_exempt
@login_required(login_url='/login/')
def events_unsubscribe(request, slug):
    events_subscription = EventsSubscription.objects.get(user=request.user) # XXX handle exceptions
    committee_events_subscription.delete() # XXX handle exceptions
    return HttpResponse('unsubscribe()d')


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


# This function handles notifications from the queue that includes
# a list of recently updated orgs,people,bills,events
def worker_handle_notification_loaddata(update_since, updated_orgs_ids, updated_people_ids, updated_bills_ids, updated_events_ids):
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
        print("doing bill action subscriptions for user" , user.username)

        # 1) Get all the bills in updated_bills_ids for which we are subscribed.
        # 2) For each of those bills, figure out if some action has occurred or will occur after the last time we updated the subscription (can this happen?)

        ba_subscriptions = BillActionSubscription.objects.filter(bill_id__in=updated_bills_ids, user=user).order_by('bill_id__slug')
        #print ("ba_subscriptions=",ba_subscriptions)
        for ba_subscription in ba_subscriptions:
            b = ba_subscription.bill
            # Look for recent actions which are more recent than the last time we updated
            actions = b.actions.order_by('-date')
            #print ("actions are: ")
            for a in actions:
                #print (a.date)
                if (a.date < ba_subscription.last_datetime_updated):
                    #print ("action date", a.date, "is < than", ba_subscription.last_datetime_updated)
                    pass
                else:
                    #print ("FOUND: action date", a.date, "is >= than", ba_subscription.last_datetime_updated)
                    bill_action_updates.append((b, a)) # add a (Bill, Action) tuple to the list

    # XXXXXX TODO: handle 1) person updates, 2) committee action updates, 3) committee event updates, 4) bill search updates, 5) all event updates
                    
    worker_send_email(user, person_updates, committee_action_updates, committee_event_updates, bill_search_updates, bill_action_updates, events_updates)
                    
# Sends a templated email based on the updates, similar to the 'Manage Subscriptions' page
def worker_send_email(user, person_updates, committee_action_updates, committee_event_updates, bill_search_updates, bill_action_updates, events_updates):
    ctx = {
        'person_updates': person_updates, # A list of bills
        'committee_action_updates': committee_action_updates, # A list of actions
        'committee_event_updates': committee_event_updates, # A list of events
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
    updated_orgs_ids = json.loads(request.POST.get('updated_orgs_ids'))
    updated_people_ids = json.loads(request.POST.get('updated_people_ids'))
    updated_bills_ids = json.loads(request.POST.get('updated_bills_ids'))
    updated_events_ids = json.loads(request.POST.get('updated_events_ids'))

    print('update_since=', update_since)
    print('updated_orgs_ids=', updated_orgs_ids)
    print('updated_people_ids=', updated_people_ids)
    print('updated_bills_ids=', updated_bills_ids)
    print('updated_events_ids=', updated_events_ids)
    
    print("notifications/views.py:new OCD data detected by loaddata.py: %d orgs, %d people, %d bills, %d events" % (len(updated_orgs_ids), len(updated_people_ids), len(updated_bills_ids), len(updated_events_ids)))
    
    # now let Redis know
    # According to http://python-rq.org/docs/ , uses pickle
    notifications_queue = django_rq.get_queue('notifications')
    notifications_queue.enqueue(worker_handle_notification_loaddata,
                                update_since=update_since,
                                updated_orgs_ids = updated_orgs_ids,
                                updated_people_ids = updated_people_ids,
                                updated_bills_ids = updated_bills_ids,
                                updated_events_ids = updated_events_ids)

    return HttpResponse('ok')


