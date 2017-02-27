django-councilmatic
===========

 The django-councilmatic app provides the core functionality for the `Councilmatic family <http://www.councilmatic.org/>`_, a set of web apps for keeping tabs on local city council. It is built upon the open civic data standard and ultimately makes Councilmatic easier to re-deploy in new cities.

django-councilmatic includes:

- data models for bills, people, organizations, events, and more
- a task to load data from the open civic data api
- views and templates for bill/person/organization/event pages, search, and more

The `Councilmatic family <http://www.councilmatic.org/>`_ includes:

- Philly Councilmatic (the original and first Councilmatic, by Mjumbe Poe, an important predecessor to DataMade's django-councilmatic)
- `Chicago Councilmatic <https://github.com/datamade/chi-councilmatic>`_
- `New York City Councilmatic <https://github.com/datamade/nyc-councilmatic>`_
- `Los Angeles Metro Board <https://github.com/datamade/la-metro-councilmatic>`_

Councilmatic in your city
----
If you're interested in bringing Councilmatic to your city, `contact us <mailto:info@councilmatic.org>`_! We'd love to help.

Want to build your own Councilmatic? Check out our `Starter Template <https://github.com/datamade/councilmatic-starter-template>`_. It contains everything you need to create your own Councilmatic from scratch.

Running tests
----
Did you make changes to django-councilmatic? Before you make a pull request, run some tests. We test for style with `flake8 <http://flake8.pycqa.org/en/latest/>`_:

```bash
flake8 ./councilmatic_core/*.py
```

We test for functionality with a custom-made `TestCase`. Be sure to specify the owner of your psql databse in the export command:

```bash
export db_user='yourusername' && python runtests.py
```

Team
----

-  Forest Gregg, DataMade - Open Civic Data (OCD) and Legistar scraping
-  Cathy Deng, DataMade - data models and loading
-  Derek Eder, DataMade - front end
-  Eric van Zanten, DataMade - search and dev ops

Patches and Contributions
-------------
We continue to improve django-councilmatic, and we welcome your ideas! You can make suggestions in the form of `github issues <https://github.com/datamade/django-councilmatic/issues>`_ (bug reports, feature requests, general questions), or you can submit a code contribution via a pull request.

How to contribute code:

- Fork the project.
- Make your feature addition or bug fix.
- Bonus points for running tests to check python style (:code:`pip install flake8` and then :code:`flake8 .`).
- Send us a pull request with a description of your work! Don't worry if it isn't perfect - think of a PR as a start of a conversation, rather than a finished product.

Copyright
---------

Copyright (c) 2015 Participatory Politics Foundation and DataMade.
Released under the `MIT
License <https://github.com/datamade/django-councilmatic/blob/master/LICENSE>`__.
