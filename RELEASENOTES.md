# Release notes for django-councilmatic

## Version 0.9.2

*Changes*

Changes the `downloads` path to insure that data resides in Councilmatic instances, rather than `django-councilmatic`. This reverts a change in in the 0.9.0 release. 

**Release date:** 3-22-2018

## Version 0.9.1

*Changes*

Makes consistent the legislative_session_id on the bill model with other data sources (e.g., OCD legislative identifier). This fixes a bug in the previous release. 

**Release date:** 3-19-2018

## Version 0.9.0

*Changes*

**Release date:** 3-19-2018

Allows for data from multiple jurisdictions by replacing `JURISDICTION_ID` setting with `JURISDICTION_IDS`, an array of OCD API jurisdiction IDs.

Adds `Jurisdiction` model.

Returns only unique identifiers from `alternative_identifiers` template filter.

## Version 0.8.10-0.8.11

*Changes*

**Release date:** 2-27-2018

Substitutes instances of `session.get` with `_get_response` - a custom function that sets a timeout of 60 seconds on HTTP requests and raises an error for bad responses. 

Pin `django-adv-cache-tag` to version 1.1.0.

## Version 0.8.9

*Changes*

**Release date:** 2-16-2018

Includes a new management command that tests for agreement between the Councilmatic database and Solr index. 

Makes amendments to `import_data`:
* Adds `html_text` to bills when it exists.
* Refactors code redundancies for readability.

## Version 0.8.8

*Changes*

**Release date:** 1-31-2018

Includes a new management command that converts bill text from RTF to HTML.

Makes amendments to `import_data`:
* Generates a `last_action_date` for bills.
* Imports `rtf_text` rather than `ocr_full_text`.
* Removes the integration of `send_notifications` and `update_index` at the end of a data import. (Assumes that the Councilmatic app calls these commands separately in a cronjob.)

Responsive table for legislation types on About page.

## Version 0.8.7

**Release date:** 12-11-2017

*Changes*

Speeds up RSS feed load by removing unneeded list evaluations and minimizing object size.

## Version 0.8.6

**Release date:** 12-07-2017

*Changes*

Raises an error on the legislation search page when Councilmatic cannot connect to Solr.

## Version 0.8.5

**Release date:** 11-28-2017

*Changes*

Adds a `guid` field in the Event model, and imports it when available in the OCD API.

## Version 0.8.4

**Release date:** 11-13-2017

*Changes*

Adds a client for improved Sentry logging when import_data fails or rolls back a transaction. 

## Version 0.8.3

**Release date:** 11-7-2017

*Changes*

Amends `import_data` codebase: imports shape data, only when the response from the OCD API returns an 'ok' status code. 

## Version 0.8.2

**Release date:** 11-6-2017

*Changes*

Adds an `updated_at` field to the EventDocument model. This field facilitates the addition of labels, which may indicate changes to upcoming events (e.g., the use of coded labels in [LA Metro](https://github.com/datamade/la-metro-councilmatic/blob/master/lametro/templatetags/lametro_extras.py#L159)). 

Add a Subject model and a one-to-many relation between Bill and Subject (i.e., one bill can have many subjects/topics). See the following examples:

* [OpenCivicData](https://ocd.datamade.us/ocd-bill/b07ef50c-20f1-431a-9257-3dddd57e0a08/)
* [Metro Councilmatic code](https://github.com/datamade/la-metro-councilmatic/blob/master/lametro/search_indexes.py#L44)
* [Councilmatic UI](https://boardagendas.metro.net/board-report/2016-0630/)


Add a RelatedBill model. This facilitates the creation of relations among bills, if the Legistar admins chose to create those, as with LA Metro:

* [Metro Councilmatic code](https://github.com/datamade/la-metro-councilmatic/blob/a2c84f7bdeaf1dec5f05cf37ad9374806c30a946/lametro/views.py#L79)
* [Councilmatic UI](https://boardagendas.metro.net/board-report/2017-0584/)

Better management of AgendaItems to prevent duplicates: in this relese, import_data deletes old agenda items, before importing new ones.

Enforce a rollback in the event of an IntegrityError.

## Prior versions

See [commit history](https://github.com/datamade/django-councilmatic/commits/master) for prior changes.
