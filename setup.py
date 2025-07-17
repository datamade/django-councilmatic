import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.dirname(__file__), "README.md")) as readme:
    README = readme.read()

requirements = {
    "core": [
        "Django>=4.2,<5",
        "opencivicdata>=3.1",
        "django-proxy-overrides>=0.2.1",
    ],
    "search": [
        "django-haystack[elasticsearch]",
        "textract",
    ],
    "cms": [
        "wagtail>=5",
        "django-storages[s3]",
    ],
}

setup(
    name="django-councilmatic",
    python_requires=">=3.9",
    version="5.0",
    packages=find_packages(),
    include_package_data=True,
    license="MIT License",
    description="Core models and optional search and CMS layers for councilmatic.org family",
    long_description=README,
    url="http://councilmatic.org/",
    author="DataMade, LLC",
    author_email="info@datamade.us",
    install_requires=requirements["core"],
    extras_require={
        "search": requirements["search"],
        "cms": requirements["cms"],
        "all": [*requirements["search"], *requirements["cms"]],
    },
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
)
