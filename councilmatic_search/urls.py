from django.urls import path, include


urlpatterns = [
    path("search/", include("haystack.urls")),
]
