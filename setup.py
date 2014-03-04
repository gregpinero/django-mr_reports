import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-mr_reports',
    version='0.1',
    packages=['mr_reports'],
    include_package_data=True,
    #license='TDB',  # example license
    description='A Django app to make simple, opinionated reports.',
    long_description=README,
    url='https://github.com/gregpinero',
    author='Greg Pinero',
    author_email='gregpinero@gmail.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        #'License :: OSI Approved :: TBD License', # example license
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)

