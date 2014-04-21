
"""
Re-usable generic functions, and handling special tasks like emailing reports
"""
import datetime
import re

from django.test.client import Client
from django.core.mail import EmailMultiAlternatives
from django.http import QueryDict, HttpRequest
from django.db import transaction
from django.utils import timezone

from models import Report, Subscription, Parameter
from views import render_report
from django.conf import settings

# Keep all DB access for a given Subscription within one txn to potentially allow 
# multiple concurrent Subscription runners.
@transaction.atomic
def execute_subscription(sched_id, force_run=False, today=None):
    """Handles creating the report PDF and sending the email.
    (A future optimzation could re-use the PDF if multiple Subscriptions of 
    the same report are running at the same time.)

    'today' defaults to current day, but you can set different dates for testing.

    This accepts the ID instead of the object itself in order to handle concurrancy issues.

    (It would seem to make sense to put this method with the Subscription model, however it leads to 
    some circular imports so it was cleaner to break it out into a utility function)."""

    #Locks record until this function completes
    sched_obj = Subscription.objects.select_for_update().get(pk=sched_id)

    #check whether we should send
    if not force_run:
        if not sched_obj.should_send(today=today):
            return False
        sched_obj.last_scheduled_run = timezone.localtime(timezone.now())
    
    if not getattr(settings, 'MR_REPORTS_WKHTMLTOPDF_PATH','') and getattr(settings, 'BASE_PATH',''):
        sched_obj.last_run_succeeded = False
        sched_obj.save()
        raise ValueError("PDF generation not available. Please add and set 'MR_REPORTS_WKHTMLTOPDF_PATH', and 'BASE_PATH' in your settings.py file.")

    #Generate PDF
    mock_request = HttpRequest()
    mock_request.method = 'GET'
    if sched_obj.report_parameters:
        mock_request.GET = QueryDict(sched_obj.report_parameters.lstrip('?'))
    else:
        #If the report has parameters and none are provided, provide dummy GET data
        if Parameter.objects.filter(dataset__report=sched_obj.report):
            mock_request.GET = QueryDict('use_defaults')

    response = render_report(mock_request, report_id=sched_obj.report.pk, format='pdf')

    #Send email
    full_url = settings.BASE_PATH.rstrip('/') + sched_obj.report.get_absolute_url()
    message = """\
Greetings,<br><br>

This is a snapshot of the report '%s'.<br><br>

Go here to view the realtime version of the report and/or change your subscription: <br>
<a href="%s">%s</a>
<br><br>
    """ % (sched_obj.report.title, full_url, full_url)
    message += sched_obj.email_body_extra
    subject = 'Scheduled Report - ' + sched_obj.email_subject
    text_content = re.sub(r'<[^>]+>','',message)
    html_content = message
    msg = EmailMultiAlternatives(subject, text_content, sched_obj.send_to.email, [sched_obj.send_to.email])
    msg.attach_alternative(html_content, "text/html")
    msg.attach(sched_obj.report.filename()+'.pdf', response.content, response['Content-Type'])
    msg.send()
    sched_obj.last_run_succeeded = True
    sched_obj.save()
    return True
