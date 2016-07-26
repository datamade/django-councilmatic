from django.db import models

from django.contrib.auth.models import User
from councilmatic_core.models import Bill, Organization, Person

from django.contrib.postgres.fields import JSONField


# XXX: Consider having some global notifications configuration model/data such as a flag for NOT sending notifications (e.g. if you need to drop and reload the whole OCD dataset)

class Subscription(models.Model):
    # Each Subscription will have:
    # - A user ID
    # - A type of subscription:
    #    1) PersonSubscription: recent sponsorships by a person
    #    2) CommitteeActionSubscription: recent actions taken by a committee
    #    3) CommitteeEventSubscription: recent events for a committee
    #    4) BillSearchSubscription: recent legislation for a given faceted search
    #    5) BillActionSubscription: actions on individual bills
    #    6) EventsSubscription: all events (e.g. https://nyc.councilmatic.org/events/ )

    user = models.ForeignKey(User, related_name='%(class)ss', db_column='user_id')    
    last_datetime_updated = models.DateTimeField(auto_now=True) #XXX

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
    search_term = models.CharField(max_length=256) # string model # XXX TODO: add an index using (automatic) migrations
    search_facets = JSONField() # XXX TODO: Add "GIN" index using manual RunSQL migration (http://michael.otacoo.com/postgresql-2/postgres-9-4-feature-highlight-indexing-jsonb/)
    
class BillActionSubscription(Subscription):
    bill = models.ForeignKey(Bill, related_name = 'subscriptions')

class EventsSubscription(Subscription):
    # This subscribes to all recent/upcoming events as per https://github.com/datamade/nyc-councilmatic/issues/175
    # XXX: not implemented yet
    pass
