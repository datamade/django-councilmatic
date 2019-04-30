# Release notes for django-councilmatic

## Version 0.10.16

*Changes*

Fixes a tricky bug in `import_data`, where specifying `update_since` would result in unexpected behavior in later imports. Flushes and reimports subjects of bills during import, in order to capture the removal of subjects.

**Release date:** 4-30-2019

## Version 0.10.15

*Changes*

Refactors the `data_integrity` management script by adding `count_councilmatic_bills` – an easy-to-override helper function.

**Release date:** 3-1-2019

## Version 0.10.14

*Changes*

Adds a `restict_view` boolean field to the Bill model, and updates `import_data` to populate this field.

**Release date:** 2-8-2019

## Version 0.10.13

*Changes*

Modifies the `convert_rtf` management command (used by NYC Councilmatic): now, the script converts by default the most recently updated bills in the Councilmatic database (`updated_at`), not the most recently updated bills in the OCD database (`ocd_updated_at`).

**Release date:** 2-1-2019

## Version 0.10.12

*Changes*

Modifies `import_data`, so that the script removes the contents of the `downloads` directory at the end of every import. It does this by default; users have the option to call the command with `--keep_downloads`.

Fixes a bug in `import_data`: now, the import considers all bills related to an event agenda item, not just the first one. 

**Release date:** 1-29-2019

## Version 0.10.11

*Changes*

Removes the `restrict_view` field (reverts changes in 0.10.9). 

**Release date:** 10-17-2018

## Version 0.10.10

*Changes*

Properly logs the results of `refresh_pic`.

**Release date:** 10-16-2018

## Version 0.10.9

*Changes*

Adds a custom script that determines if bill and event documents have been modified and, if so, deletes them from DataMade's S3 bucket `councilmatic-document-cache`. Running this script requires including an AWS_KEY and AWS_SECRET in the settings file. 

Adds a `restict_view` boolean field to the Bill model, and updates `import_data` to populate this field.

**Release date:** 10-16-2018

## Version 0.10.8

*Changes*

Captures `extras` for Membership model.

**Release date:** 10-8-2018

## Version 0.10.7

*Changes*

Adds an ExactHighlighter class, which enables highlighting multi-word strings via Haystack. 

Adds "nofollow" attribute to Legistar links to improve search rankings.  

**Release date:** 9-7-2018

## Version 0.10.6

*Changes*

Fixes a bug in the search functionality (wherein the `order_by` param was not preserved in the query string).

**Release date:** 8-2-2018

## Version 0.10.5

*Changes*

Passes `GOOGLE_API_KEY` into relevant templates. This change requires adding the new variable to `settings_deployment.py`.

**Release date:** 7-30-2018

## Version 0.10.4

*Changes*

Refactors template and view logic for sorting search results by date, title, and relevance.

Updates `import_data` to grab the `plain_text` for EventAgendaItems.

Bug fix: Removes `full_text` from the Solr `bill_text` template. (Instances of Councilmatic need to `rebuild_index` to benefit from this change.)

**Release date:** 7-24-2018

## Version 0.10.3

*Changes*

Breaks search bar into its own partial for downstream override.

**Release date:** 5-31-2018

## Version 0.10.2

*Changes*

Replaces Event.guid field with generic Event.extras field, which accepts an
object containing arbitrary keys and values for downstream customizations.

**Release date:** 5-7-2018

## Version 0.10.1

*Changes*

Fixes bug in EventMedia init method.

**Release date:** 5-2-2018

## Version 0.10.0

*Changes*

Adds support for multiple event media links, by introducing an `EventMedia`
model, and removing `media_url` from the `Event` model.

**Release date:** 4-13-2018

## Version 0.9.5

*Changes*

Adds a management command (`convert_attachment_text`) that converts bill attachments into plain text. [LA Metro Councilmatic](https://github.com/datamade/la-metro-councilmatic) uses this script. 

**Release date:** 4-9-2018

## Version 0.9.4

*Changes*

Increases the chunk size within migration number 0038 to increase processing time. 

**Release date:** 4-3-2018

## Version 0.9.3

*Changes*

Adds two migrations that unmangle NYC and Chicago Councilmatic bill identifiers and slugs, specifically: adds leading zeroes, and removes unwanted space. 

**Release date:** 4-3-2018

## Version 0.9.2

*Changes*

Changes the path to `downloads` in `import_data`: this insures that downloaded data resides in Councilmatic instances, rather than `django-councilmatic`. This reverts a change in the 0.9.0 release. 

**Release date:** 3-22-2018

## Version 0.9.1

*Changes*

Makes consistent the legislative_session_id on the bill model with other data sources (e.g., OCD legislative identifier). This fixes a bug in the previous release. 

**Release date:** 3-19-2018

## Version 0.9.0

*Changes*

Allows for data from multiple jurisdictions by replacing `JURISDICTION_ID` setting with `JURISDICTION_IDS`, an array of OCD API jurisdiction IDs.

Adds `Jurisdiction` model.

Returns only unique identifiers from `alternative_identifiers` template filter.

**Release date:** 3-19-2018

## Version 0.8.10-0.8.11

*Changes*

Substitutes instances of `session.get` with `_get_response` - a custom function that sets a timeout of 60 seconds on HTTP requests and raises an error for bad responses. 

Pin `django-adv-cache-tag` to version 1.1.0.

**Release date:** 2-27-2018

## Version 0.8.9

*Changes*

Includes a new management command that tests for agreement between the Councilmatic database and Solr index. 

Makes amendments to `import_data`:
* Adds `html_text` to bills when it exists.
* Refactors code redundancies for readability.

**Release date:** 2-16-2018

## Version 0.8.8

*Changes*

Includes a new management command that converts bill text from RTF to HTML.

Makes amendments to `import_data`:
* Generates a `last_action_date` for bills.
* Imports `rtf_text` rather than `ocr_full_text`.
* Removes the integration of `send_notifications` and `update_index` at the end of a data import. (Assumes that the Councilmatic app calls these commands separately in a cronjob.)

Responsive table for legislation types on About page.

**Release date:** 1-31-2018

## Version 0.8.7

*Changes*

Speeds up RSS feed load by removing unneeded list evaluations and minimizing object size.

**Release date:** 12-11-2017

## Version 0.8.6

*Changes*

Raises an error on the legislation search page when Councilmatic cannot connect to Solr.

**Release date:** 12-07-2017

## Version 0.8.5

*Changes*

Adds a `guid` field in the Event model, and imports it when available in the OCD API.

**Release date:** 11-28-2017

## Version 0.8.4

*Changes*

Adds a client for improved Sentry logging when import_data fails or rolls back a transaction. 

**Release date:** 11-13-2017

## Version 0.8.3

*Changes*

Amends `import_data` codebase: imports shape data, only when the response from the OCD API returns an 'ok' status code. 
**Release date:** 11-7-2017

## Version 0.8.2

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

**Release date:** 11-6-2017