from django.conf.urls import url
from . import views
from . import feeds
import notifications

from django.contrib import admin
admin.autodiscover() # XXX necessary?

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^about/$', views.AboutView.as_view(), name='abouts'),
    url(r'^committees/$', views.CommitteesView.as_view(), name='committees'),
    url(r'^council-members/$', views.CouncilMembersView.as_view(),
        name='council_members'),

    url(r'^committee/(?P<slug>[^/]+)/$',
        views.CommitteeDetailView.as_view(), name='committee_detail'),
    url(r'^committee/(?P<slug>[^/]+)/events/rss/$',
        feeds.CommitteeDetailEventsFeed(), name='committee_detail_events_feed'),
    url(r'^committee/(?P<slug>[^/]+)/events/subscribe/$',
        notifications.views.committee_events_subscribe, name='committee_events_subscribe'),
    url(r'^committee/(?P<slug>[^/]+)/events/unsubscribe/$',
        notifications.views.committee_events_unsubscribe, name='committee_events_unsubscribe'),
    url(r'^committee/(?P<slug>[^/]+)/actions/rss/$',
        feeds.CommitteeDetailActionFeed(), name='committee_detail_action_feed'),
    url(r'^committee/(?P<slug>[^/]+)/actions/subscribe/$',
        notifications.views.committee_actions_subscribe, name='committee_actions_subscribe'),
    url(r'^committee/(?P<slug>[^/]+)/actions/unsubscribe/$',
        notifications.views.committee_actions_unsubscribe, name='committee_actions_unsubscribe'),
    url(r'^committee/(?P<slug>[^/]+)/widget/$',
        views.CommitteeWidgetView.as_view(), name='committee_widget'),

    url(r'^legislation/(?P<slug>[^/]+)/$',
        views.BillDetailView.as_view(), name='bill_detail'),
    url(r'^legislation/(?P<slug>[^/]+)/rss/$',
        feeds.BillDetailActionFeed(), name='bill_detail_action_feed'),
    url(r'^legislation/(?P<slug>[^/]+)/widget/$',
        views.BillWidgetView.as_view(), name='bill_widget'),

    url(r'^person/(?P<slug>[^/]+)/$', views.PersonDetailView.as_view(), name='person'),
    url(r'^person/(?P<slug>[^/]+)/rss/$', feeds.PersonDetailFeed(), name='person_feed'),
    url(r'^person/(?P<slug>[^/]+)/widget/$',
        views.PersonWidgetView.as_view(), name='person_widget'),

    url(r'^events/$', views.EventsView.as_view(), name='events'),
    url(r'^event/(?P<slug>[^/]*)/$',
        views.EventDetailView.as_view(), name='event_detail'),

    url(r'^flush-cache/(.*)/$', views.flush, name='flush'),
    url(r'^pdfviewer/$', views.pdfviewer, name='pdfviewer'),
]
