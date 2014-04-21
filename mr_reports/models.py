
"""
TODO:

Ability to refresh report and get re-prompted for parameters
Allow datasets for parameters ...?
Ability to log out for normal users
Categories
advanced permissions
pagination, sorting
Better handling of parameters for subscriptions, they're error prone and not
    user friendly.  I think I could include and validate each parameter within
    a subscription form.  See http://stackoverflow.com/questions/4727732/django-add-field-to-model-formset
Show sql and connection info for each table for debugging

South:
(mr_reports)[pinerog@pinero-ws reports]$ python manage.py schemamigration mr_reports --auto
(mr_reports)[pinerog@pinero-ws reports]$ python manage.py migrate mr_reports

"""
import datetime
import re
import ast

from django.db import models
from django.contrib.auth.models import Group, User
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone

from encrypted_fields import EncryptedCharField
import sqlalchemy
from sqlalchemy.sql import text

from maybe_safe_eval import safe_eval as maybe_safe_eval


class AuditableTable(models.Model):
    """A basic abstract table to save timestamp info when object is created or 
    changed and hold fields for created by and updated by"""
    class Meta:
        abstract = True
    created_datetime = models.DateTimeField(auto_now_add=True, editable=False)
    updated_datetime = models.DateTimeField(auto_now=True, editable=False)
    #These should be filled in from admin or view save methods as required:
    created_by = models.ForeignKey(User,blank=True, null=True,
        related_name="%(app_label)s_%(class)s_related1")
    last_updated_by = models.ForeignKey(User,blank=True, null=True,
        related_name="%(app_label)s_%(class)s_related2")


class DataConnection(AuditableTable):
    """How to connect to a datasource.  This uses sqlalchemy behind the scenes.
    See http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html for details"""
    class Meta:
        verbose_name_plural = "Data Connections"

    drivername = models.CharField(max_length=100,
        help_text="The name of the database backend. This name will correspond "
        "to a module in sqlalchemy/databases or a third party plug-in. Examples: mysql, sqlite")
    dialect = models.CharField(max_length=100, blank=True,
            help_text="Optionally used for certain drivers.  For example, use "
            "'oursql' for OurSQL")
    username = models.CharField(max_length=300, blank=True)
    password = EncryptedCharField(passphrase_setting='SECRET_KEY', max_length=300,
        help_text="WARNING: Assume this is not safe! It is encrypted using unvetted code I "
        "found on the internet.  It will be encrypted when stored in " 
        "the database BUT the key is stored on your sever. "
        " It will also be available to any users using the admin interface and "
        "is sent to the DB server and to admin users in clear text.", blank=True)
    host = models.CharField(max_length=300, help_text="The name of the host", blank=True)
    port = models.IntegerField(help_text="The port number", null=True, blank=True)
    database = models.CharField(max_length=300, help_text="The database name")

    def get_db_connection(self):
        url = sqlalchemy.engine.url.URL(drivername=self.drivername, username=self.username or None,
            password=self.password or None, host=self.host or None, port=self.port or None, database=self.database)
        #Sqlalchemy doesn't seem to let us specify dialect in URL, I guess we have to hack it in??
        s_url = str(url)
        if self.dialect:
            drivername,the_rest = str(url).split('://')
            s_url = drivername + '+' + self.dialect + '://' + the_rest
        engine = sqlalchemy.create_engine(s_url)
        return engine.connect()

    def __unicode__(self):
        return "%s@%s/%s (%s)" % (self.username, self.host, self.database, self.drivername)

def totwotuple(tupl): #convenience function
    return tuple([tuple([item]*2) for item in tupl])
class Parameter(AuditableTable):
    """Specify optional parameters that a given report can ask for"""
    name = models.CharField(help_text="Name used in queries, only valid Python variable names please.", max_length=255,
        unique=True)
    label = models.CharField(max_length=300, blank=True, help_text="What this parameter will be called on the report.")
    comment = models.CharField(max_length=300, blank=True)
    #Should match Django field types
    data_type = models.CharField(max_length=300, 
        choices=totwotuple(('BooleanField','CharField','DateField','DateTimeField','DecimalField',
        'IntegerField','TimeField')))
    python_create_default = models.TextField(help_text="This should be blank for no default. Or python code "
        "that sets a variable named 'default' to what you would like the default to be. (datetime module has already been imported)",
        blank=True)
    required = models.BooleanField(help_text="Is this parameter required to allow the report to run.")
    #Coming soon:
    #javascript defaults    
    #validations

    def create_default(self):
        default = None
        if self.python_create_default and getattr(settings,'MR_REPORTS_ALLOW_NATIVE_PYTHON_CODE_EXEC_ON_SERVER',False):
            #Pre-supply context with white-listed imports.  WARNING: this is probably a security risk!
            #If adding more imports here, also update maybe_safe_eval.modules_whitelist, and put a reload a few lines down.
            import datetime
            context = {'datetime':datetime}
            #Django saves newlines with \r\n, but to eval we just want \n (or we'll get a syntax error)
            code_to_run = self.python_create_default.replace('\r\n','\n')
            maybe_safe_eval(code_to_run, context = context, timeout_secs = 5)
            #pull out calculated default value
            default = context['default']
            #Reload any whitelisted modules (in case semi-untrusted code messed with them.)
            #(Won't always help but it's better than nothing)
            reload(datetime)
        return default

    def clean(self):
        # Don't allow whitespace, special characters in parameter names
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', self.name):
            raise ValidationError("Name must start with a letter or '_', and can only contain letters, '_'s or numbers.")
        # Don't allow setting required=True when providing a default value, that would confuse things ...
        if self.python_create_default and self.required:
            raise ValidationError("A parameter with a default value cannot be set to required.")            

    def edit_link(self):
        return mark_safe("<a href='/admin/mr_reports/parameter/%s/'>Edit</a>" % self.id)

    def __unicode__(self):
        return self.name

class DataSet(AuditableTable):
    """A query to pull data"""
    name = models.CharField(max_length=50)
    label = models.CharField(help_text="Optional label to appear above data set on report", blank=True,max_length=200)
    connection = models.ForeignKey(DataConnection)
    query = models.TextField(help_text="A SQL query to run. If using parameters, use parameter names "
        "after ':'. Here's an example with a parameter named 'pawnum': select earsize from dogs where numpaws=:pawnum")
    parameters = models.ManyToManyField(Parameter, blank=True, null=True, through='DataSetParameter')
    python_post_processing = models.TextField(help_text="Optional python code. Your code will have access to a list of lists called 'data' "
        "with all of the data.  Modify this as you see fit.",
        blank=True)

    def run_query(self, submitted_parameters):
        conn = self.connection.get_db_connection() #TODO: re-use across object
        query = text(self.query)
        if submitted_parameters:
            result = conn.execute(query, **submitted_parameters.cleaned_data)
        else:
            result = conn.execute(query)

        columns = [item[0] for item in result.cursor.description]        
        data = result.fetchall()

        #Python post processing on data (if any)
        if self.python_post_processing and getattr(settings,'MR_REPORTS_ALLOW_NATIVE_PYTHON_CODE_EXEC_ON_SERVER',False):
            context = {'data':data}
       	    #Django saves newlines with	\r\n, but to eval we just want \n (or we'll get	a syntax error)
      	    code_to_run	= self.python_post_processing.replace('\r\n','\n')
            maybe_safe_eval(code_to_run, context = context, timeout_secs = 10)
            #pull out calculated default value
            data = context['data']

        return data, columns

    def edit_link(self):
        return mark_safe("<a href='/admin/mr_reports/dataset/%s/'>Edit</a>" % self.id)

    def name_for_id(self):
        """make name useable as a CSS id"""
        return re.sub(r'[^a-zA-Z0-9_\-]','-',self.name)

    def __unicode__(self):
        return self.name

class DataSetParameter(models.Model):
    """Special model to track many to many relationship between a dataset and parameters"""
    class Meta:
        ordering = ['dataset', 'order_on_form']
    dataset = models.ForeignKey(DataSet)
    parameter = models.ForeignKey(Parameter)
    order_on_form = models.IntegerField(default=0, help_text="Enter a number greater than or equal to 0 to specify "
        "which order this parameter should be displayed on the form. Lower numbers come first")


class Style(AuditableTable):
    """Custom CSS for a report"""
    name = models.CharField(max_length=100)
    css = models.TextField()

    def __unicode__(self):
        return self.name


class Report(AuditableTable):
    """This is an actual report, made up for one or more datasets."""
    title = models.CharField(max_length=200)
    byline = models.CharField(max_length=300, blank=True)
    html_instructions = models.TextField("Instructions (HTML)", blank=True,
        help_text=escape("Any special instructions or details about reading or using this report. Use <br/> for line breaks, and <a> tags for links."))
    datasets = models.ManyToManyField(DataSet, help_text="These datasets will be "
        "displayed as tables on the report.", through='ReportDataSet')
    style = models.ForeignKey(Style, blank=True, null=True,
        help_text="Optional CSS styles to apply to the report")
    js_post_processing = models.TextField(help_text="Custom javascript to add charts, "
        "move tables, format data or do anything else you desire. ! Make sure to inclue script tags !", blank=True)
    pdf_paper_size = models.CharField(max_length=20,
                                      choices=totwotuple(('Letter','Legal','Ledger','Tabloid','Folio','A0',
                                                          'A1','A2','A3','A4','A5','A6','A7','A8','A9','B1','B2',
                                                          'B3','B4','B5','B6','B7','B8','B9','B10','C5E','DLE','Executive')),
                                      default='Letter')
    pdf_orientation = models.CharField(max_length=20,
                                      choices=totwotuple(('Portrait','Landscape')),
                                      default='Portrait')

    #Files such as images that will be available for JS code to optionally use (coming soon!)
    #files_available = ...

    def update_submitted_parameters_w_defaults(self, submitted_parameters):
        """If a user submits a form leaving a field with a default value blank, we want 
        to fill it in with a default value.
        (since the parameter form on the report is built dynamically it's better to do this here.)
        """
        if submitted_parameters:
            for pname, value in submitted_parameters.cleaned_data.items():
                p = Parameter.objects.get(name=pname)
                if not value and p.python_create_default:
                    submitted_parameters.cleaned_data[pname] = p.create_default()
        return submitted_parameters

    def get_all_data(self, submitted_parameters=None):
        submitted_parameters = self.update_submitted_parameters_w_defaults(submitted_parameters)

        #Run queries to get datasets
        datasets = []
        for reportdataset in self.reportdataset_set.all().order_by('order_on_report'):
            dataset = reportdataset.dataset
            data, columns = dataset.run_query(submitted_parameters)
            columns = [col.replace('_',' ').title() for col in columns]
            datasets.append((dataset,data,columns))
        return datasets

    def get_absolute_url(self):
        return reverse('mr_reports.views.report', args=[str(self.id)])

    def filename(self):
        """Return a title usable for filenames"""
        return re.sub(r'[^a-zA-Z0-9_\-]','-',self.title)

    def view_report(self):
        return mark_safe("<a href='%s'>%s</a>" % (self.get_absolute_url(),self.get_absolute_url()))

    def __unicode__(self):
        return self.title


class ReportDataSet(models.Model):
    """Special model to track many to many relationship between a report and datasets"""
    class Meta:
        ordering = ['report', 'order_on_report']
    report = models.ForeignKey(Report)
    dataset = models.ForeignKey(DataSet)
    order_on_report = models.IntegerField(default=0, help_text="Enter a number greater than or equal to 0 to specify "
        "which order this dataset should be displayed on the report. Lower numbers come first")

class Subscription(models.Model):
    """Controls who gets emailed which reports when."""
    class Meta:
        ordering = ['-last_scheduled_run','pk']
    send_to = models.ForeignKey(User)
    report = models.ForeignKey(Report)
    #Note: This handling of report_parameters needs to be overhauled if subscriptions are popular. 
    #it's not user friendly and is error prone.
    report_parameters = models.CharField(max_length=1000, blank=True,
        help_text="This should be the query string of the URL of a succussfullly running report. " \
        "Example: as_of_date=2014-03-21&test_parameter1=on. Leave this field blank to use default report parameters.")
    time = models.TimeField(help_text="Report will be sent as close to this time of day as possible. Example input: 6:00")
    start_date = models.DateField(help_text="This is the date the first report will be sent. "
        "For monthly and yearly subscriptions, they will re-occur on this day. (Daiy and Weekly will be sent every 24 hours or 7 days respectively "
        "from the start_date and time.)")
    frequency = models.CharField(max_length=20,
      choices=totwotuple(('Daily','Weekly','Monthly','Yearly')), default='Monthly')
    email_subject = models.CharField(max_length=200, blank=True)
    email_body_extra = models.TextField(blank=True)
    last_scheduled_run = models.DateTimeField(null=True, editable=False)
    last_run_succeeded = models.BooleanField(default=False, editable=False)

    def should_send(self, today=None):
        """Determines whether this schedule should fire at the current time

        (today defaults to current day, but you can set different dates for testing.)
        """
        if today:
            tt = timezone.make_aware(today, timezone.get_default_timezone())
        else:
            tt = timezone.localtime(timezone.now())
        t = tt.date()

        last_run = self.last_scheduled_run or datetime.datetime.min.replace(tzinfo=timezone.utc)
        time_since_last_run = tt - last_run

        seconds_since_last_run = time_since_last_run.seconds + (time_since_last_run.days * 24 * 3600)

        hours_since_last_run = seconds_since_last_run / 3600.0
        days_since_last_run = seconds_since_last_run / (3600.0 * 24)

        if tt.time() >= self.time and t >= self.start_date:

            if self.frequency == 'Daily' and hours_since_last_run >= 24:
                return True
            elif self.frequency == 'Weekly' and days_since_last_run >= 7:
                return True
            elif (self.frequency == 'Monthly') and ((self.start_date.day == t.day) or (days_since_last_run > 31)):
                return True
            elif (self.frequency == 'Yearly') and ((t.month == self.start_date.month and t.day == self.start_date.day) \
                or (days_since_last_run >= 366)):
                return True

        return False

    def clean(self):
        # I didn't have a clever way to handle monthly/yearly schedules when starting
        # in short months so we won't allow days above the shortest month 
        if self.start_date and self.start_date.day > 28:
            raise ValidationError("Please choose a start date on or before the 28th of a given month.")

    def __unicode__(self):
        return "Send %s to %s %s" % (self.report, self.send_to, self.frequency)

