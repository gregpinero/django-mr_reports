from django.conf.urls import patterns, url

from mr_reports import views

urlpatterns = patterns('',
    # ex: /reports/
    url(r'^$', views.index, name='index'),
    # ex: /reports/5/
    url(r'^(?P<report_id>\d+)/$', views.report, name='report'),
    url(r'^(?P<report_id>\d+)/(?P<format>\w+)/$', views.report, name='report'),
)
