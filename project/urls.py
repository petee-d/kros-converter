from django.conf.urls import url

from converter.views import index, convert, health

urlpatterns = [
    url(r'^$', index),
    url(r'^convert$', convert),
    url(r'^health$', health),
]
