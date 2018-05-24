from django.conf import settings
from django.conf.urls import include, url

from converter.views import index, convert, health

urlpatterns = [
    url(r'^$', index),
    url(r'^convert$', convert),
    url(r'^health$', health),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
