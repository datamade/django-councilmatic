django-councilmatic
===================

The django-councilmatic app provides the core functionality for the `Councilmatic family <http://www.councilmatic.org/>`_, a set of web apps for keeping tabs on local city council. It is built upon the Open Civic Data standard and ultimately makes Councilmatic easier to re-deploy in new cities.


Features
--------

- Models for bills, people, organizations, events, and more
- Base views for Bill, Person, Organization, and Event listing and detail pages
- Search infrastructure powered by :code:`django-haystack` and Solr

The `Councilmatic family <http://www.councilmatic.org/>`_ includes:

- Philly Councilmatic (the original and first Councilmatic, by Mjumbe Poe, an important predecessor to DataMade's django-councilmatic)
- `Chicago Councilmatic <https://github.com/datamade/chi-councilmatic>`_
- `New York City Councilmatic <https://github.com/datamade/nyc-councilmatic>`_
- `Los Angeles Metro Board <https://github.com/datamade/la-metro-councilmatic>`_


Councilmatic in your city
-------------------------
If you're interested in bringing Councilmatic to your city, `contact us <mailto:info@councilmatic.org>`_! We'd love to help.

Want to build your own Councilmatic? Check out our `Starter Template <https://github.com/datamade/councilmatic-starter-template>`_. It contains everything you need to create your own Councilmatic from scratch.


Extending Open Civic Data/Councilmatic models
---------------------------------------------

django-councilmatic leverages, and in some instaances, lightly extends the Open Civic Data Standard, implemented in Django as :code:`python-opencivicdata`. If you'd like to add additional attributes or Python properties to your models, there are two approaches to be aware of: subclassing and proxying.

Subclassing
===========

Leverage `multi-table inheritance <https://docs.djangoproject.com/en/2.2/topics/db/models/#multi-table-inheritance>`_ to add additional fields to OCD models. The primary use case in django-councilmatic is adding slugs to first-class models – Person, Event, Bill, and Organization - and adding metadata outside of the OCD standard, e.g., a headshot to Person and division boundaries to Post.

We recommend using :code:`pupa` to scrape legislative data. Since :code:`pupa` creates OCD objects, `django-councilmatic includes Django signals <https://github.com/datamade/django-councilmatic/pull/240/files#diff-97cdca8c3c4b594b1991875f343b7db5>`_ to each of the subclassed models to create the related Councilmatic model on save. It also includes management commands to import metadata (see above).

If you subclass a model, be sure to include a signal to create instances of your subclass when the parent class is created, and, if applicable, some way to add any metadata, e.g., a management command or admin interface.

Proxying
========

django-councilmatic makes extensive use of proxy models to add custom managers and additional properties and methods to model classes. In order to take advantage of these elsewhere in the code, it is desirable for related objects to be returned as instances of other proxy classes or subclasses, rather than the upstream OCD model classes. In order to force related objects to be returned as Councilmatic models, django-councilmatic makes use of `django-proxy-overrides <https://github.com/datamade/django-proxy-overrides>`_.

If you wish to customize the class of related objects, first proxy an OCD model, then override one or more of its related object attributes with an instance of `ProxyForeignKey`. See `councilmatic_core.models.BillAction <https://github.com/datamade/django-councilmatic/blob/449ff74d3968b0f34016698d4ee89ff50a7b33ef/councilmatic_core/models.py#L612>`_ for an example.


Running tests
-------------

Did you make changes to django-councilmatic? Before you make a pull request, run some tests.

First, install the test requirements:

.. code-block:: bash

    pip install -r tests/requirements.txt

We test for style with `flake8 <http://flake8.pycqa.org/en/latest/>`_:

.. code-block:: bash

    flake8 ./councilmatic_core/*.py

We test for functionality with `pytest`:

.. code-block:: bash

    pytest

If you made material changes to the Councilmatic models, refresh the test fixture from a local instance database. From your instance directory (assuming you've already installed :code:`django-councilmatic` with :code:`pip install -e /path/to/django-councilmatic`), install the test requirements:

.. code-block:: bash

    pip install -r /path/to/django-councilmatic/tests/test_requirements.txt

Add :code:`fixture_magic` to your instance's :code:`INSTALLED_APPS` in :code:`settings.py`.

Run the management command to update the test fixture.

.. code-block:: bash

    python manage.py make_fixtures

Run the tests and commit your updated fixture with your PR!


Patches and Contributions
-------------------------
We continue to improve django-councilmatic, and we welcome your ideas! You can make suggestions in the form of `github issues <https://github.com/datamade/django-councilmatic/issues>`_ (bug reports, feature requests, general questions), or you can submit a code contribution via a pull request.

How to contribute code:

- Fork the project.
- Make your feature addition or bug fix.
- Bonus points for running tests to check python style (:code:`pip install flake8` and then :code:`flake8 .`).
- Send us a pull request with a description of your work! Don't worry if it isn't perfect - think of a PR as a start of a conversation, rather than a finished product.


Copyright
---------

Copyright (c) 2019 Participatory Politics Foundation and DataMade.
Released under the `MIT
License <https://github.com/datamade/django-councilmatic/blob/master/LICENSE>`__.
