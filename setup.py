import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.dirname(__file__), "README.rst")) as readme:
    README = readme.read()

setup(
    name="django-councilmatic",
    python_requires=">=3.6",
    version="4.0",
    packages=find_packages(),
    include_package_data=True,
    license="MIT License",
    description="Core models for councilmatic.org family",
    long_description=README,
    url="http://councilmatic.org/",
    author="DataMade, LLC",
    author_email="info@datamade.us",
    install_requires=[
        "opencivicdata>=3.1.0",
        "pytz>=2015.4",
        "Django>=3.2,<3.3",
        "django-proxy-overrides>=0.2.1",
    ],
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
