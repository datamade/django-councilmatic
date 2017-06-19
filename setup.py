import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-councilmatic',
    version='0.8.1',
    packages=['councilmatic_core'],
    include_package_data=True,
    license='MIT License',  # example license
    description='Core functions for councilmatic.org family',
    long_description=README,
    url='http://councilmatic.org/',
    author='DataMade, LLC',
    author_email='info@datamade.us',
    install_requires=['requests==2.7.0',
                      'pytz==2015.4',
                      'django-haystack==2.5.0',
                      'Django<1.10',
                      'pysolr==3.3.3',
                      'python-dateutil==2.4.2',
                      'SQLAlchemy==1.1.2',
                      'psycopg2==2.6.2',
                      'django-password-reset==0.9',
                      'django-councilmatic-notifications<0.2',
                      'django-adv-cache-tag'],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',  # example license
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        # Replace these appropriately if you are stuck on Python 2.
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
