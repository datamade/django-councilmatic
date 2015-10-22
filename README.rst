django-councilmatic
===========

This is a Django app with core functions for the `Councilmatic family <http://www.councilmatic.org/>`_, a set of web apps for keeping tabs on local city council. It is built upon the open civic data standard, and ultimately makes Councilmatic easier to re-deploy in new cities.

django-councilmatic includes:

- data models for bills, people, organizations, events, and more
- a task to load data from the open civic data api
- views & templates for bill/person/organization/event pages, search, and more

The `Councilmatic family <http://www.councilmatic.org/>`_ includes:

- Philly Councilmatic (the original & first Councilmatic, by Mjumbe Poe. since it preceded django-councilmatic, it does not use django-councilmatic)
- Chicago Councilmatic (the live website doesn't use django-councilmatic, but we are actively re-building it)
- New York City Councilmatic (launched & built on django-councilmatic)

Councilmatic in your city
----
If you're interested in bringing Councilmatic to your city, `contact us <mailto:info@councilmatic.org>`_! We'd love to help.

Team
----

-  David Moore - project manager
-  Forest Gregg - Open Civic Data (OCD) and Legistar scraping
-  Cathy Deng - data models and loading
-  Derek Eder - front end
-  Eric van Zanten - search and dev ops

Errors / Bugs
-------------

If something is not behaving intuitively, it is a bug, and should be
reported. Report it here:
https://github.com/datamade/django-councilmatic/issues

Note on Patches/Pull Requests
-----------------------------

-  Fork the project.
-  Make your feature addition or bug fix.
-  Commit, do not mess with rakefile, version, or history.
-  Send a pull request. Bonus points for topic branches.

Copyright
---------

Copyright (c) 2015 Participatory Politics Foundation and DataMade.
Released under the `MIT
License <https://github.com/datamade/chi-councilmatic/blob/master/LICENSE>`__.
