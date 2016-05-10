from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^about/$', views.AboutView.as_view(), name='abouts'),
    url(r'^committees/$', views.CommitteesView.as_view(), name='committees'),
    url(r'^council-members/$', views.CouncilMembersView.as_view(),
        name='council_members'),
    url(r'^committee/(?P<slug>[^/]+)/$',
        views.CommitteeDetailView.as_view(), name='committee_detail'),
    url(r'^legislation/(?P<slug>[^/]+)/$',
        views.BillDetailView.as_view(), name='bill_detail'),
    url(r'^person/(?P<slug>[^/]+)/$', views.PersonDetailView.as_view(), name='person'),
    url(r'^events/$', views.EventsView.as_view(), name='events'),
    url(r'^event/(?P<slug>.*)/$',
        views.EventDetailView.as_view(), name='event_detail'),
    url(r'^flush-cache/(.*)/$', views.flush, name='flush'),
    url(r'^pdfviewer/$', views.pdfviewer, name='pdfviewer'),
    url(r'^committee/(?P<slug>[^/]+)/widget/$',
        views.CommitteeWidgetView.as_view(), name='committee_widget'),
    url(r'^legislation/(?P<slug>[^/]+)/widget/$',
        views.BillWidgetView.as_view(), name='bill_widget'),
    url(r'^person/(?P<slug>[^/]+)/widget/$',
        views.PersonWidgetView.as_view(), name='person_widget'),
]
