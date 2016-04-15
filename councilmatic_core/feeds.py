from .models import Person, Bill, Organization, Event, Post
from datetime import date, timedelta, datetime
import itertools
from operator import attrgetter
import urllib
from django.contrib.syndication.views import Feed

import pytz
import re
import json

class CommitteeDetailFeed(Feed):
    description_template = 'feeds/committee_detail_description.html'

    #TODO mcc: determine if get_context_data() is necessary for feed
    #def get_context_data(self, **kwargs):
    #    print ("get_context_data()")
    #    context = super(CommitteeDetailFeed, self).get_context_data(**kwargs)
    #    print ("context is " + str( context))
    #    committee = context['committee']
    #    print("committee is ", committee, "!!")
    #    return context

    def get_object(self, request, slug):
        o = Organization.objects.get(slug=slug)
        return o
    
    def title(self, obj):
        return obj.name

    def link(self, obj):
        return obj.source_url

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
        return "Events for committee  %s" % obj.name
        pass

    def items(self, obj):
        events =  obj.recent_events[:30]
        return events
    
