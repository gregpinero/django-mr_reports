
"""
Custom manage.py command to send scheduled reports.

"""
import traceback

from django.core.management.base import BaseCommand, CommandError
from mr_reports.models import Subscription, Report
from mr_reports.utils import execute_subscription

class Command(BaseCommand):
    help = 'Emails the scheduled reports (subscriptions) that are ready to be sent'

    def handle(self, *args, **options):
        #Go through each schedule and determine if it's time to send it
        for sched in Subscription.objects.all():
            try:
                sent = execute_subscription(sched.id)
            except Exception, e:
                self.stdout.write("Hit error on schedule: %s:" % sched)
                self.stdout.write(traceback.format_exc())
            else:
                self.stdout.write('Attempted to send "%s". Was sent = %s' % (sched,sent))
        self.stdout.write("Finished run")
