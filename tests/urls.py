from django.apps import apps
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),
]

if apps.is_installed("councilmatic_search"):
    urlpatterns += [path("", include("councilmatic_search.urls"))]

# Wagtail's catch-all page route must come last
if apps.is_installed("councilmatic_cms"):
    urlpatterns += [path("", include("councilmatic_cms.urls"))]
