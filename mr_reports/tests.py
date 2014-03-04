
"""
Some very basic tests.  More to come soon!
"""
import os
import sqlite3
from django.test import TestCase

from mr_reports.models import Report, Parameter, DataSet, DataConnection, \
    DataSetParameter, ReportDataSet

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
        #import pdb;pdb.set_trace()
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

    def tearDown(self):
        #delete sample test db
        os.remove('sample_test.db')

    def test_pulling_data(self):
        """A basic report can pull data from sqlite"""
        report = Report.objects.get(title="test")
        (_, data, columns) = report.get_all_data()[0]
        self.assertEqual(data, [(u'2006-01-05', u'BUY', u'RHAT', 100.0, 35.14)])
        self.assertEqual(columns, ['Date', 'Trans', 'Symbol', 'Qty', 'Price'])

