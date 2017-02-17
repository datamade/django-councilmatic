from django.conf.urls import url, include
from django.views.generic import RedirectView

from django.contrib import admin

from django.conf import settings

from . import views
from . import feeds

admin.autodiscover()


urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^search/$', RedirectView.as_view(), name='search'),
    url(r'^about/$', views.AboutView.as_view(), name='about'),
    url(r'^committees/$', views.CommitteesView.as_view(), name='committees'),
    url(r'^council-members/$', views.CouncilMembersView.as_view(),
        name='council_members'),
    url(r'^committee/(?P<slug>[^/]+)/$',
        views.CommitteeDetailView.as_view(), name='committee_detail'),
    url(r'^committee/(?P<slug>[^/]+)/events/rss/$',
        feeds.CommitteeDetailEventsFeed(), name='committee_detail_events_feed'),
    url(r'^committee/(?P<slug>[^/]+)/actions/rss/$',
        feeds.CommitteeDetailActionFeed(), name='committee_detail_action_feed'),
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
    url(r'^events/rss/$', feeds.EventsFeed(), name='events_feed'),
    url(r'^event/(?P<slug>.+)/$',
        views.EventDetailView.as_view(), name='event_detail'),

    url(r'^flush-cache/(.*)/$', views.flush, name='flush'),
    url(r'^pdfviewer/$', views.pdfviewer, name='pdfviewer'),
]

if (settings.USING_NOTIFICATIONS):
    urlpatterns.extend([
        url(r'', include('notifications.urls')),
    ])
