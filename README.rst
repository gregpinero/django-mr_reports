=====
Mr. Reports
=====

Mr. Reports is a Django app to provide simple, opinionated* reports with attractive
styling (using Bootstrap), and all the must-have report features like Excel and PDF downloads.

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


Quick start
-----------
1. Install:
        pip install django-mr_reports

2. Add "mr_reports" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = (
        'mr_reports',
    )

3. Include the mr_reports URLconf in your project urls.py like this::

    url(r'^reports/', include('mr_reports.urls')),

4. Make sure the Django admin is enabled and set up.  That is how you'll edit/manage reports.

5. Update your settings.py with additional settings as needed.  See Settings section below.

6. Run `python manage.py syncdb` to create the mr_reports models.

7. Start the development server and visit http://127.0.0.1:8000/reports/
to see a listing of reports.  Visit the admin panel to start writing reports.

8. Install wkhtmltopdf to enable PDF export of reports.


Updating settings.py
-----------

Make sure your SECRET_KEY is set. This is used to attempt to obscure database connection passwords.

Other optional settings:

#Customize what goes on the bottom of all reports
MR_REPORTS_FOOTER_HTML = '<p><em>Report by Mr. Reports <a href="https://github.com/gregpinero">(Code)</a></em></p>'

#Use for PDF generation of reports
MR_REPORTS_WKHTMLTOPDF_PATH = '/path/to/wkhtmltopdf'
MR_REPORTS_WKHTMLTOPDF_OPTIONS = [
    #'--print-media-type', 
]

Experimental settings:

#Allow your report developing users (anyone with access to report/parameter objects on admin
#site) to execute Python code on your server.  
#!!! Very dangereous, only enable if you know what you're doing !!!
MR_REPORTS_ALLOW_NATIVE_PYTHON_CODE_EXEC_ON_SERVER = False

