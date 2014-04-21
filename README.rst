=====
Mr. Reports
=====

Mr. Reports is a Django app to provide simple, opinionated* report generation 
(now called business intelligence) with attractive styling (using Bootstrap), 
and all the must-have report features like Excel and PDF downloads, and 
scheduled emails.

Reports, data connections, data sets (queries), and report parameters are all 
managed through the Django admin.

WARNING: This is in alpha mode so be careful.  Also don't store important database passwords 
until the security code has been vetted.

How are the reports opinionated?

Just like Python itself, the philosophy here is easy things should be easy and 
hard things should be possible.

So this app makes a lot of decisions and defaults for you to save you time. For 
example, the results from your dataset (query) are rendered as a table on the report
as is, there's no need to muck about with layout, name columns, etc. 

(But if you do want to muck with the layout, each report allows custom CSS and Javascript.)

Detailed documentation is in the "docs" directory and [TODO]

Screenshots
-----------

A sample report:

.. image:: mr_reports/docs/screenshots/sample_report.png?raw=true

Edit and create reports through Django's admin console:

.. image:: mr_reports/docs/screenshots/editing_reports.png?raw=true

Editing a sample report:

.. image:: mr_reports/docs/screenshots/editing_a_report.png?raw=true

Quick start
-----------
#. Install::

    pip install django-mr_reports

#. Add "mr_reports" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = (
        'mr_reports',
    )

#. Include the mr_reports URLconf in your project urls.py like this::

    url(r'^reports/', include('mr_reports.urls')),

#. Make sure the Django admin is enabled and set up.  That is how you'll edit/manage reports.

#. Update your settings.py with additional settings as needed.  See Settings section below.

#. Run `python manage.py syncdb` to create the mr_reports models.

#. Start the development server and visit http://127.0.0.1:8000/reports/ to see a listing of reports.  Visit the admin panel to start writing reports.

#. Install wkhtmltopdf to enable PDF export of reports.

#. To enable scheduled reports/subscriptions:

##. Make sure PDF export is set up and working

##. Make sure email is set up for your Django project

##. Set up a cron job to run this command periodically: python manage.py send_scheduled_reports


Updating settings.py
-----------

Make sure your SECRET_KEY is set. This is used to attempt to obscure database connection passwords.

It's best to make sure a timezone is set to make scheduled reports work correctly. Example:
TIME_ZONE = 'America/New_York'
USE_TZ = True



Other optional settings::

    #Customize what goes on the bottom of all reports
    MR_REPORTS_FOOTER_HTML = '<p><em>Report by Mr. Reports <a href="https://github.com/gregpinero">(Code)</a></em></p>'

    #Use for PDF generation of reports
    MR_REPORTS_WKHTMLTOPDF_PATH = '/path/to/wkhtmltopdf'
    MR_REPORTS_WKHTMLTOPDF_OPTIONS = [
        '--javascript-delay', '1000',
    ]
In order for PDF export to work make sure to specify BASE_PATH in settings so wkhtmltopdf knows
how to find the server.  The server must be running at this URI in order for PDF export to work.
Example:

    BASE_PATH = 'http://10.101.10.172:8002/'    

Experimental settings::

    #Allow your report developing users (anyone with access to report/parameter objects on admin
    #site) to execute Python code on your server.  
    #!!! Very dangereous, only enable if you know what you're doing !!!
    MR_REPORTS_ALLOW_NATIVE_PYTHON_CODE_EXEC_ON_SERVER = False

