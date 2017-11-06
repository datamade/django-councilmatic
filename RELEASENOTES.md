# Release note for django-councilmatic

## Version 0.8.2

**Release date:** 11-6-2017

*Changes*

Adds an `updated_at` field to the EventDocument model. This change facilitates the addition of labels that indicate changes to upcoming event (e.g., the use of coded labels in [LA Metro](https://github.com/datamade/la-metro-councilmatic/blob/master/lametro/templatetags/lametro_extras.py#L159)). 

Add a Subject model and a one-to-many relation between Bill and Subject (one bill can have many subjects/topics). See the following examples:

* [OpenCivicData](https://ocd.datamade.us/ocd-bill/b07ef50c-20f1-431a-9257-3dddd57e0a08/)
* [Metro Councilmatic code](https://github.com/datamade/la-metro-councilmatic/blob/master/lametro/search_indexes.py#L44)
* [Councilmatic UI](https://boardagendas.metro.net/board-report/2016-0630/)


Added a RelatedBill model. This facilitates the creation of relations among bills, if the Legistar admins chose to create those, as with LA Metro:

* [Metro Councilmatic code](https://github.com/datamade/la-metro-councilmatic/blob/a2c84f7bdeaf1dec5f05cf37ad9374806c30a946/lametro/views.py#L79)
* [Councilmatic UI](https://boardagendas.metro.net/board-report/2017-0584/)

Better management of AgendaItems to prevent duplicates: in this relese, import_data deletes all old items, before importing new ones.

Enforce a rollback in the event of an Integrity error.