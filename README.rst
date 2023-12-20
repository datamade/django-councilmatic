django-councilmatic
===================

The django-councilmatic app provides the core models for the `Councilmatic family <http://www.councilmatic.org/>`_, a set of web apps for keeping tabs on local city council.

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


Copyright
---------

Copyright (c) 2023 Participatory Politics Foundation and DataMade.
Released under the `MIT
License <https://github.com/datamade/django-councilmatic/blob/master/LICENSE>`__.
