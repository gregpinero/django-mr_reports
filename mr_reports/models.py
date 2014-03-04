
"""
TODO:
Package and deploy to github,
Allow datasets for parameters ...?
Have way to generate report PDF's for emailing, need special logon? maybe just allow scheduling?
advanced permissions
pagination?
requested form order isn't always being respeced, investigate

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
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.urlresolvers import reverse

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
        "the database BUT the password is stored on your sever. "
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

def totwotuple(tupl):
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

    def edit_link(self):
        return mark_safe("<a href='/admin/mr_reports/parameter/%s/'>Edit</a>" % self.id)

    def __unicode__(self):
        return self.name

class DataSet(AuditableTable):
    """A query to pull data"""
    name = models.CharField(max_length=50)
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
        if self.connection.dialect.lower() == 'oursql':
            #Sql alchemy / oursql is throwing an error for result.fetchall() so pull one by one?
            data = [list(result.fetchone()) for i in range(result.rowcount)]
        else:
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

    def get_all_data(self, submitted_parameters=None):
        #Run queries to get datasets
        datasets = []
        for dataset in self.datasets.all():
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



