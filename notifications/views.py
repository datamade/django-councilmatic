from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin

from councilmatic_core.models import Bill, Organization, Person
from notifications.models import PersonSubscription, BillActionSubscription, CommitteeActionSubscription, CommitteeEventSubscription

import rq

from redis import Redis

import django_rq
import json

# XXX put this in some more appropriate/official place such as notifications/__init__.py
# XXX Also: could in theory have different queues for difft types of notifications!
#notifications_queue= Queue('notifications',connection=Redis())
# redis_conn = django_rq.get_connection('notifications')
notifications_queue= django_rq.get_queue('notifications')  

def notifications_login(request):
    if request.method == 'POST':
        print("notifications_login(): POST", request.POST)
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                login(request, user)
                #return HttpResponseRedirect(reverse('notifications.views.subscriptions_manage'))
                return HttpResponseRedirect(reverse('index'))
    else:
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


@login_required(login_url='/login/')
def subscriptions_add(request):
    return HttpResponse('subscriptions_add')

@login_required(login_url='/login/')
def subscriptions_delete(request):
    return HttpResponse('subscriptions_delete')

# things you might do include:
# - subscribe to sponsored legislation by a committee member
# - subscribe to actions by a given committee
# - subscribe to events for a given committee
# - subscribe to actions on an individual bill
# - subscribe to a particular search string

@login_required(login_url='/login/')
def bill_subscribe(request, slug):
    # using the model BillActionSubscription using the current user and the Bill
    bill = Bill.objects.get(slug=slug)
    (bill_action_subscription, created) = BillActionSubscription.objects.get_or_create(user=request.user, bill=bill)
    print ("bill_action_subscription is ", bill_action_subscription)
    return HttpResponse('subscribed to bill %s ' % str(bill))

@login_required(login_url='/login/')
def bill_unsubscribe(request, slug):
    bill = Bill.objects.get(slug=slug)
    bill_action_subscription = BillActionSubscription.objects.get(user=request.user, bill=bill)

    # delete it! XXX: handle exceptions
    bill_action_subscription.delete()
    
    return HttpResponse('bill_unsubscribe eyyy')

@login_required(login_url='/login/')
def person_subscribe(request, slug):
    # using the model PersonSubscription using the current user and the Person defined by slug
    person = Person.objects.get(slug=slug)
    (person_subscription, created) = PersonSubscription.objects.get_or_create(user=request.user, person=person)

    print ("person_subscription is ", person_subscription)
    return HttpResponse('person_subscribe()d')

@login_required(login_url='/login/')
def person_unsubscribe(request, slug):
    person = Person.objects.get(slug=slug)
    person_subscription = PersonSubscription.objects.get(user=request.user, person=person)

    # delete it!! XXX handle exceptions
    person_subscription.delete()
    
    return HttpResponse('person_unsubscribe()d')

@login_required(login_url='/login/')
def committee_events_subscribe(request, slug):
    committee = Organization.objects.get(slug=slug)
    (committee_events_subscription, created) = CommitteeEventSubscription.objects.get_or_create(user=request.user, committee=committee)

    print ("committee_events_subscription is ", committee_events_subscription)
    return HttpResponse('person subscribe()d to committee event')

@login_required(login_url='/login/')
def committee_events_unsubscribe(request, slug):
    committee = Organization.objects.get(slug=slug)
    committee_events_subscription = CommitteeEventSubscription.objects.get(user=request.user, committee=committee)

    # XXX handle exceptions
    committee_events_subscription.delete()
    
    return HttpResponse('unsubscribe()d')


@login_required(login_url='/login/')
def committee_actions_subscribe(request, slug):
    committee = Organization.objects.get(slug=slug)
    (committee_actions_subscription, created) = CommitteeActionSubscription.objects.get_or_create(user=request.user, committee=committee)

    print ("committee_actions_subscription is ", committee_actions_subscription)
    return HttpResponse('person subscribe()d to committee event')

@login_required(login_url='/login/')
def committee_actions_unsubscribe(request, slug):
    #XXX YAH
    committee = Organization.objects.get(slug=slug)
    committee_actions_subscription = CommitteeActionSubscription.objects.get(user=request.user, committee=committee)

    # XXX handle exceptions
    committee_actions_subscription.delete()
    
    return HttpResponse('unsubscribe()d')


# XXX: use this function to handle notifications from the queue that includes
# a list of recently updated orgs,people,bills,events
def worker_handle_notification_loaddata(updated_orgs_ids, updated_people_ids, updated_bills_ids, updated_events_ids):
    # check each user's subscriptions and send off emails
    print ("WORKER_HANDLE_NOTIFICATION_LOADDATA()")
    print (updated_orgs_ids)
    print (updated_people_ids)
    print (updated_bills_ids)
    print (updated_events_ids)
    pass

# this is posted to by management/loaddata.py
@csrf_exempt
def notification_loaddata(request):
    if request.method != 'POST':
        print("ERROR: notifications/views.py:notification_loaddata() called without POST")

    updated_orgs_ids = json.loads(request.POST.get('updated_orgs_ids'))
    updated_people_ids = json.loads(request.POST.get('updated_people_ids'))
    updated_bills_ids = json.loads(request.POST.get('updated_bills_ids'))
    updated_events_ids = json.loads(request.POST.get('updated_events_ids'))

    print('updated_orgs_ids=', updated_orgs_ids)
    print('updated_people_ids=', updated_people_ids)
    print('updated_bills_ids=', updated_bills_ids)
    print('updated_events_ids=', updated_events_ids)
    
    print("notifications/views.py:new stuff detected by loaddata.py: %d orgs, %d people, %d bills, %d events" % (len(updated_orgs_ids), len(updated_people_ids), len(updated_bills_ids), len(updated_events_ids)))
    
    # now let Redis know
    # XXX According to http://python-rq.org/docs/ , uses pickle
    notifications_queue = django_rq.get_queue('notifications')
    notifications_queue.enqueue(worker_handle_notification_loaddata,
                                updated_orgs_ids = updated_orgs_ids,
                                updated_people_ids = updated_people_ids,
                                updated_bills_ids = updated_bills_ids,
                                updated_events_ids = updated_events_ids)

    return HttpResponse('ok')


