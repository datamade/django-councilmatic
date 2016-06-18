from django.db import models

from django.contrib.auth.models import User
from councilmatic_core.models import Bill, Organization, Person

from django.contrib.postgres.fields import JSONField

# Create your models here.

class Subscription(models.Model):
    # Each Subscription will have:
    # - A user ID
    # - A type (?) of subscription:
    #    1) recent sponsorships by a committee member (need the committee member slug/id)
    #    2) recent actions taken by a committee (need the committee slug/id)
    #    3) recent events for a committee (need the committee slug/id)
    #    4) recent legislation for a given faceted search (need to store that search string)
    #    5) actions on individual bills (need the bill slug/id)

    user = models.ForeignKey(User, related_name='%(class)ss', db_column='user_id')    
    last_datetime_updated = models.DateTimeField(auto_now=True) #XXX

    #def fire_notification(self):
    #    pass
    #def get_(self):
    #    pass
    
    # Make this an abstract base class
    class Meta:
        abstract = True
    
    pass


class PersonSubscription(Subscription):
    # related_name lets us go from the user to their committee member subscriptions
    person = models.ForeignKey(Person, related_name = 'subscriptions')

class CommitteeActionSubscription(Subscription):
    committee = models.ForeignKey(Organization, related_name = 'subscriptions_actions')
    
class CommitteeEventSubscription(Subscription):
    committee = models.ForeignKey(Organization, related_name = 'subscriptions_events')
    
class BillSearchSubscription(Subscription):
    search_term = models.CharField(max_length=256) # string model
    search_facets = JSONField() # XXX
    
class BillActionSubscription(Subscription):
    bill = models.ForeignKey(Bill, related_name = 'subscriptions')

