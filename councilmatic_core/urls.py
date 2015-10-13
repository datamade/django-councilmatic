from django.conf.urls import url
from . import views

handler404 = 'views.not_found'

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^about/$', views.AboutView.as_view(), name='abouts'),
    url(r'^committees/$', views.CommitteesView.as_view(), name='committees'),
    url(r'^council-members/$', views.CouncilMembersView.as_view(), name='council_members'),
    url(r'^committee/(?P<slug>.*)/$', views.CommitteeDetailView.as_view(), name='committee_detail'),
    url(r'^legislation/(?P<slug>.*)/$', views.BillDetailView.as_view(), name='bill_detail'),
    url(r'^person/(?P<slug>.*)/$', views.PersonDetailView.as_view(), name='person'),
    url(r'^login/$', views.user_login, name='user_login'),
    url(r'^logout/$', views.user_logout, name='user_logout'),
    url(r'^events/$', views.events, name='events'),
    url(r'^events/(.*)/(.*)/$', views.events, name='events'),
    url(r'^event/(.*)/$', views.event_detail, name='event_detail'),
]
