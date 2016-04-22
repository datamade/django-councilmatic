from .models import Person, Bill, Organization, Event, Post
from datetime import date, timedelta, datetime
import itertools
from operator import attrgetter
import urllib
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Rss201rev2Feed
from django.core.urlresolvers import reverse

import pytz
import re
import json

class PersonDetailFeed(Feed):
    title_template = 'feeds/person_detail_item_title.html'
    description_template = 'feeds/person_detail_item_description.html'
    feed_type = Rss201rev2Feed
    NUM_RECENT_BILLS = 20
    
    def get_object(self, request, slug):
        o = Person.objects.get(slug=slug)
        return o
    
    def title(self, obj):
        return "%s: Recent Sponsored Bills" % obj.name

    def link(self, obj):
        # return the Councilmatic URL for the person
        # XXX maybe put this in models.py:Person.get_absolute_url() instead (https://docs.djangoproject.com/en/1.9/ref/models/instances/ , https://docs.djangoproject.com/en/1.9/ref/contrib/syndication/)
        return reverse('person', args=(obj.slug,))

    # Return sponsored legislation a la https://nyc.councilmatic.org/person/margaret-s-chin/
    def item_link(self, bill):
        # return the Councilmatic URL for the bill
        return reverse('bill_detail', args=(bill.slug,))

    def item_title(self, bill):
        return bill.friendly_name

    def item_description(self, bill):
        return bill.listing_description

    def item_pubdate(self, bill):
        return bill.last_action_date
    
    def description(self, obj):
        return "Recent sponsored bills from " + obj.name + "."

    def items(self, person):
        sponsored_bills = [s.bill for s in person.primary_sponsorships.order_by('-_bill__last_action_date')[:10]]
        recent_sponsored_bills = sponsored_bills[:self.NUM_RECENT_BILLS]
        return recent_sponsored_bills


class CommitteeDetailFeed(Feed):
    description_template = 'feeds/committee_detail_description.html'
    feed_type = Rss201rev2Feed
    NUM_RECENT_COMMITTEE_EVENTS = 20

    def get_object(self, request, slug):
        o = Organization.objects.get(slug=slug)
        return o
    
    def title(self, obj):
        return obj.name

    def link(self, obj):
        # return the Councilmatic URL for the committee
        return reverse('committee_detail', args=(obj.slug,))

    def item_link(self, event):
        return event.source_url

    def item_title(self, item):
        return item.name + " " + str(item.start_time) +  " " + item.location_name

    def item_description(self, event):
        agenda_items = event.clean_agenda_items()
        description = ''
        for ai in agenda_items:
            description += ai.description + "\n"
        return description

    def item_pubdate(self, event):
        return event.start_time
    
    def description(self, obj):
        return "Events for committee %s" % obj.name
        pass

    def items(self, obj):
        events =  obj.recent_events[:self.NUM_RECENT_COMMITTEE_EVENTS]
        return events
    
