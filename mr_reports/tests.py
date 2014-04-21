
"""
Some very basic tests.  More to come soon!
"""
import os
import sqlite3
import datetime
from dateutil.relativedelta import *

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from mr_reports.models import Report, Parameter, DataSet, DataConnection, \
    DataSetParameter, ReportDataSet, Subscription
from mr_reports.utils import execute_subscription

#Shortcuts
t = datetime.time
d = datetime.date
dt = datetime.datetime
nowish_w_dt = datetime.datetime.now().replace(tzinfo=timezone.get_default_timezone())
nowish = nowish_w_dt.time()
dt_today = timezone.make_aware(dt.today(), timezone.get_default_timezone())

class ReportTestCase(TestCase):
    def setUp(self):
        #Create a simple database with test data for report to connect to
        conn = sqlite3.connect('sample_test.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS stocks
                     (date text, trans text, symbol text, qty real, price real)''')
        c.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")
        conn.commit()
        conn.close()

        #Set up test objects
        dataconnection = DataConnection(drivername='sqlite', dialect='', host='',
            database='sample_test.db')
        dataconnection.save()
        parameter = Parameter(name='test', data_type='DateField', required=False)
        parameter.save()
        dataset = DataSet(name='test', connection=dataconnection, query="select * from stocks")
        dataset.save()

        DataSetParameter.objects.create(dataset=dataset, parameter=parameter)
        
        report = Report(title='test')
        report.save()

        ReportDataSet.objects.create(report=report, dataset=dataset)
   
        self.dummy_user = User.objects.create_user('dummy', 'dummy@example.com', 'password')
        self.dummy_user.save()
        self.report = report

    def tearDown(self):
        #delete sample test db
        os.remove('sample_test.db')

    def test_pulling_data(self):
        """A basic report can pull data from sqlite"""
        report = Report.objects.get(title="test")
        (_, data, columns) = report.get_all_data()[0]
        self.assertEqual(data, [(u'2006-01-05', u'BUY', u'RHAT', 100.0, 35.14)])
        self.assertEqual(columns, ['Date', 'Trans', 'Symbol', 'Qty', 'Price'])

    ### Things we don't expect to be sent:
    def test_sched_calc_1(self):
        """23 hours after last run"""
        sched = Subscription(send_to=self.dummy_user, report=self.report, frequency='Daily',
                        email_subject='nosend', time=nowish, start_date=d.today(),
                        last_scheduled_run=dt_today-relativedelta(hours=23))
        sched.save()
        self.assertFalse(sched.should_send())

    def test_sched_calc_2(self):
        """6 days since last run"""
        sched = Subscription(send_to=self.dummy_user, report=self.report, frequency='Weekly',
                        email_subject='nosend', time=nowish, start_date=d.today(),
                        last_scheduled_run=dt_today-relativedelta(days=6))
        sched.save()
        self.assertFalse(sched.should_send())

    def test_sched_calc_3(self):
        """before start date"""
        sched = Subscription(send_to=self.dummy_user, report=self.report, frequency='Monthly',
                        email_subject='nosend', time=nowish, start_date=d.today() + relativedelta(days=2),)
        sched.save()
        self.assertFalse(sched.should_send())

    def test_sched_calc_4(self):
        """25 days after last run"""
        sched = Subscription(send_to=self.dummy_user, report=self.report, frequency='Monthly',
                        email_subject='nosend', time=nowish, start_date=d.today()-relativedelta(days=25),
                        last_scheduled_run=dt_today-relativedelta(days=25))
        sched.save()
        self.assertFalse(sched.should_send())

    def test_sched_calc_5(self):
        """11 months since last run"""
        sched = Subscription(send_to=self.dummy_user, report=self.report, frequency='Yearly',
                        email_subject='nosend', time=nowish, start_date=d.today()-relativedelta(months=11),
                        last_scheduled_run=dt_today-relativedelta(months=11))
        sched.save()
        self.assertFalse(sched.should_send())

    def test_sched_calc_6(self):
        """1 year after start date, but before time"""
        sched = Subscription(send_to=self.dummy_user, report=self.report, frequency='Yearly',
                        email_subject='nosend', time=(nowish_w_dt + relativedelta(hours=2)).time(), 
                        start_date=d.today(),
                        last_scheduled_run=dt_today-relativedelta(months=13))
        sched.save()
        self.assertFalse(sched.should_send())

    ### Things we do expect to be sent

    def test_sched_calc_7(self):
        """No prior runs"""
        sched = Subscription(send_to=self.dummy_user, report=self.report, frequency='Daily',
                        email_subject='send', time=nowish, start_date=d.today())
        sched.save()
        self.assertTrue(sched.should_send())

    def test_sched_calc_8(self):
        """24.5 hours after last run"""
        sched = Subscription(send_to=self.dummy_user, report=self.report, frequency='Daily',
                        email_subject='send', time=nowish, start_date=d.today(),
                        last_scheduled_run=dt_today-relativedelta(minutes=1470))
        sched.save()
        self.assertTrue(sched.should_send())

    def test_sched_calc_9(self):
        """7 days after last run"""
        sched = Subscription(send_to=self.dummy_user, report=self.report, frequency='Weekly',
                        email_subject='send', time=nowish, start_date=d.today(),
                        last_scheduled_run=dt_today-relativedelta(days=7))
        sched.save()
        self.assertTrue(sched.should_send())

    def test_sched_calc_10(self):
        """1 year after start date"""
        sched = Subscription(send_to=self.dummy_user, report=self.report, frequency='Yearly',
                        email_subject='send', time=nowish, start_date=d.today(),
                        last_scheduled_run=dt_today-relativedelta(months=12))
        sched.save()
        self.assertTrue(sched.should_send())

    def test_sched_calc_11(self):
        """Next month on same day"""
        sched = Subscription(send_to=self.dummy_user, report=self.report, frequency='Monthly',
                        email_subject='send_feb1', time=datetime.time(0, 0),
                        start_date=d(d.today().year, 1, 1),
                        last_scheduled_run=dt_today-relativedelta(days=25))
        sched.save()
        pretend_today_is = dt(d.today().year, 2, 1)
        self.assertTrue(sched.should_send(pretend_today_is))

    def test_sched_calc_12(self):
        """11 months since last run but day and month are right"""
        sched = Subscription(send_to=self.dummy_user, report=self.report, frequency='Yearly',
                        email_subject='send', time=nowish, start_date=d.today(),
                        last_scheduled_run=dt_today-relativedelta(months=11))
        sched.save()
        self.assertTrue(sched.should_send())

    def test_sched_calc_13(self):
        """25 days after last run but day and month are correct"""
        sched = Subscription(send_to=self.dummy_user, report=self.report, frequency='Monthly',
                        email_subject='send', time=nowish, start_date=d.today(),
                        last_scheduled_run=dt_today-relativedelta(days=25))
        sched.save()
        self.assertTrue(sched.should_send())

