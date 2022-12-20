import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.dirname(__file__), "README.rst")) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name="django-councilmatic",
    python_requires=">=3.6",
    version="3.0",
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    license="MIT License",  # example license
    description="Core functions for councilmatic.org family",
    long_description=README,
    url="http://councilmatic.org/",
    author="DataMade, LLC",
    author_email="info@datamade.us",
    install_requires=[
        "requests>=2.20,<2.21",
        "opencivicdata>=3.1.0",
        "pytz>=2015.4",
        "django-haystack>=3.2,<3.3",
        "Django>=3.2,<3.3",
        "django-proxy-overrides>=0.2.1",
        "python-dateutil>=2.7,<2.8",
        "psycopg2-binary>=2.9.5",
        "django-adv-cache-tag==1.1.2",
        "boto==2.38.0",
        "tqdm",
    ],
    extras_require={"convert_docs": ["textract"]},
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",  # example license
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
)
