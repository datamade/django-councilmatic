django-councilmatic
===========

 The django-councilmatic app provides the core functionality for the `Councilmatic family <http://www.councilmatic.org/>`_, a set of web apps for keeping tabs on local city council. It is built upon the open civic data standard, and ultimately makes Councilmatic easier to re-deploy in new cities.

django-councilmatic includes:

- data models for bills, people, organizations, events, and more
- a task to load data from the open civic data api
- views & templates for bill/person/organization/event pages, search, and more

The `Councilmatic family <http://www.councilmatic.org/>`_ includes:

- Philly Councilmatic (the original & first Councilmatic, by Mjumbe Poe, an important predecessor to DataMade's django-councilmatic)
- Chicago Councilmatic (launched & built on django-councilmatic)
- New York City Councilmatic (launched & built on django-councilmatic)
- Los Angeles Metro Board (launched & built on django-councilmatic)

Councilmatic in your city
----
If you're interested in bringing Councilmatic to your city, `contact us <mailto:info@councilmatic.org>`_! We'd love to help.

Want to build your own Councilmatic? Check out our `Starter Template <https://github.com/datamade/councilmatic-starter-template>`. It contains everything you need to create your own Councilmatic from scratch.

Team
----

-  David Moore - project manager
-  Forest Gregg - Open Civic Data (OCD) and Legistar scraping
-  Cathy Deng - data models and loading
-  Derek Eder - front end
-  Eric van Zanten - search and dev ops

Patches and Contributions
-------------
We continue to improve django-councilmatic, & we welcome your ideas! You can make suggestions in the form of `github issues <https://github.com/datamade/django-councilmatic/issues>`_ (bug reports, feature requests, general questions), or you can submit a code contribution via a pull request.

How to contribute code:

- Fork the project.
- Make your feature addition or bug fix.
- Bonus points for running tests to check python style (:code:`pip install flake8` & then :code:`flake8 .`)
- Send us a pull request with a description of your work! Don't worry if it isn't perfect - think of a PR as a start of a conversation, rather than a finished product

Copyright
---------

Copyright (c) 2015 Participatory Politics Foundation and DataMade.
Released under the `MIT
License <https://github.com/datamade/chi-councilmatic/blob/master/LICENSE>`__.
