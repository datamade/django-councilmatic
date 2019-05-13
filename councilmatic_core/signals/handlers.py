from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils.text import slugify, Truncator

from opencivicdata.core.models import (Organization as OCDOrganization,
                                       Person as OCDPerson)
from opencivicdata.legislative.models import (Event as OCDEvent,
                                              Bill as OCDBill)

from councilmatic_core.models import (Organization as CouncilmaticOrganization,
                                      Person as CouncilmaticPerson,
                                      Event as CouncilmaticEvent,
                                      Bill as CouncilmaticBill,
                                      BillAction,
                                      BillSponsorship)

from haystack import connection_router, connections
from actstream import action



@receiver(post_save, sender=OCDOrganization)
def create_councilmatic_org(sender, instance, created, **kwargs):
    if created:
        ocd_part = instance.id.rsplit('-', 1)[-1]
        slug = '{0}-{1}'.format(slugify(instance.name), ocd_part)

        co = CouncilmaticOrganization(organization=instance,
                                      slug=slug)
        # just update the child table, not the parent table
        co.save_base(raw=True)


@receiver(post_save, sender=OCDPerson)
def create_councilmatic_person(sender, instance, created, **kwargs):
    if created:
        ocd_part = instance.id.rsplit('-', 1)[-1]
        slug = '{0}-{1}'.format(slugify(instance.name), ocd_part)

        cp = CouncilmaticPerson(person=instance,
                                slug=slug)
        # just update the child table, not the parent table
        cp.save_base(raw=True)

@receiver(post_save, sender=OCDEvent)
def create_councilmatic_event(sender, instance, created, **kwargs):
    if created:
        truncator = Truncator(instance.name)
        ocd_part = instance.id.rsplit('-', 1)[-1]
        slug = '{0}-{1}'.format(slugify(truncator.words(5)), ocd_part)

        ce = CouncilmaticEvent(event=instance,
                               slug=slug)
        # just update the child table, not the parent table
        ce.save_base(raw=True)

@receiver(post_save, sender=OCDBill)
def create_councilmatic_bill(sender, instance, created, **kwargs):
    if created:
        slug = slugify(instance.identifier)

        cb = CouncilmaticBill(bill=instance,
                              slug=slug)
        # just update the child table, not the parent table
        cb.save_base(raw=True)

        cb = CouncilmaticBill.objects.get(id=instance.id)
    else:
        cb = instance.councilmatic_bill

    save_haystack(cb)


def save_haystack(instance):

    using_backends = connection_router.for_write(instance=instance)

    for using in using_backends:
        index = connections[using].get_unified_index().get_index(instance.__class__)
        index.update_object(instance, using=using)

    
@receiver(pre_delete, sender=CouncilmaticBill)
def remove_haystack(sender, instance, *args, **kwargs):
    
    using_backends = connection_router.for_write(instance=instance)

    for using in using_backends:
        index = connections[using].get_unified_index().get_index(sender)
        index.remove_object(instance, using=using)

@receiver(post_save, sender=BillAction)
def bill_action_activity(sender, instance, created, **kwargs):
    if created:
        action.send(instance.organization,
                    'took action',
                    action_object=instance,
                    target=instance.bill)

@receiver(post_save, sender=BillSponsorship)        
def bill_sponsorship_activity(sender, instance, created, **kwargs):
    if created:
        if instance.person:
            action.send(instance.person,
                        'sponsored',
                        target=instance.bill)
        elif instance.organization:
            action.send(instance.organization,
                        'sponsored',
                        target=instance.bill)

@receiver(post_save, sender=CouncilmaticEvent)
def event_activity(sender, instance, created, **kwargs):
    if created:
        for participant in instance.participants.filter(note='host'):
            action.send(participant.organization,
                        'scheduled an event',
                        target=instance)
    else:
        for participant in instance.participants.filter(note='host'):
            action.send(participant.organization,
                        'updated',
                        target=instance)
            
            
