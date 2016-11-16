from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import strip_entities, strip_tags
import re

from django.utils.safestring import mark_safe
from django.core.serializers import serialize
import json
from django.db.models.query import QuerySet
import urllib

register = template.Library()


@register.filter
@stringfilter
def sentence_case(value):
    return value.replace("_", " ").capitalize()


@register.filter
@stringfilter
def inferred_status_label(status):
    return "<span class='label label-" + status.lower() + "'>" + status + "</span>"


@register.filter
@stringfilter
def facet_name(value):
    if value == 'bill_type':
        return 'Legislation type'
    if value == 'sponsorships':
        return 'Sponsor'
    if value == 'controlling_body':
        return 'Controlling body'
    if value == 'inferred_status':
        return 'Legislation status'


@register.filter
@stringfilter
def remove_action_subj(bill_action_desc):
    # removes 'by X' from bill action descriptions & expands abbrevs
    # for more readable action labels
    clean_action = re.sub(r'\bComm\b', 'Committee', bill_action_desc)
    clean_action = re.sub(r'\bRecved\b', 'Received', clean_action)
    clean_action = re.sub(r'[,\s]*by\s[^\s]*', '', clean_action)

    # shorten the really long action descriptions for approval w/ modifications
    if 'approved with modifications' in clean_action.lower():
        clean_action = 'Approved with Modifications'

    return clean_action


@register.filter
@stringfilter
def short_blurb(text_blob):
    if len(text_blob) > 196:
        blurb = text_blob[:196]
        blurb = blurb[:blurb.rfind(' ')] + ' ...'
        return blurb
    else:
        return text_blob


@register.filter
@stringfilter
def short_title(text_blob):
    if len(text_blob) > 28:
        blurb = text_blob[:24]
        blurb = blurb[:blurb.rfind(' ')] + ' ...'
        return blurb
    else:
        return text_blob


@register.filter
@stringfilter
def strip_mailto(email):
    return re.sub('mailto:', '', email)


@register.filter
@stringfilter
def committee_topic_only(committee_name):
    clean = re.sub('Committee on ', '', committee_name)
    clean = re.sub('Subcommittee on ', '', clean)
    if 'Mental Health, Developmental Disability' in clean:
        clean = 'Mental Health & Disability'
    return clean


@register.filter
@stringfilter
def clean_html(text):
    return strip_entities(strip_tags(text)).replace('\n', '')


@register.filter
@stringfilter
def alternative_identifiers(id_original):
    id_1 = re.sub(" ", " 0", id_original)
    id_2 = re.sub(" ", "", id_original)
    id_3 = re.sub(" ", "", id_1)
    return id_original + ' ' + id_1 + ' ' + id_2 + ' ' + id_3


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def format_date_sort(s, fmt='%Y%m%d%H%M'):
    if s:
        return s.strftime(fmt)
    else:
        return '0'

# Used in subscriptions_manage.html. XXX: potential (?) site of concern for injecting JSON in search facet dicts and re-jsonifying it there
# (From https://stackoverflow.com/questions/4698220/django-template-convert-a-python-list-into-a-javascript-object )
# Open ticket in Django (with discussion of problematic aspects) https://code.djangoproject.com/ticket/17419
@register.filter
def jsonify(object):
    if isinstance(object, QuerySet):
        return mark_safe(serialize('json', object))
    return mark_safe(json.dumps(object))
jsonify.is_safe = True

# Given a search subscription object, successfully reconstruct the
# URL representing it
@register.filter
def custom_reverse_search_url(subscription):
    url = '/search/'
    d = [('q',subscription.search_term)]
    for k,vs in subscription.search_facets.items():
        #print ("k=",k, "vs=",vs)
        for v in vs:
            #print ("k=",k, "v=",v)
            d.append(("selected_facets","%s_exact:%s" % (k,v)))
    url += "?" + urllib.parse.urlencode(d)
    #print ("custom_reverse_search_url: url is=", url)
    return url


@register.filter
def format_url_parameters(url):
    params = {"?&sort_by=date": "", "?&sort_by=title": "", "?&sort_by=relevance": ""}

    paramsDict = dict((re.escape(k), v) for k, v in params.items())
    pattern = re.compile("|".join(paramsDict.keys()))

    return pattern.sub(lambda m: paramsDict[re.escape(m.group(0))], url)

# TODO: Clean up for refactor of javascript.
# @register.simple_tag
# def query_transform(request, **kwargs):

#     data_dict = dict(request.GET.copy())
#     print(data_dict)
#     try:
#         selected_facet_names = data_dict['selected_facets']
#     except:
#         selected_facet_names = []

#     updated = request.GET.copy()
#     if selected_facet_names:
#         for k,v in kwargs.items():
#             selected_facet_names.append(v)

#     updated['selected_facets'] = selected_facet_names

#     return updated.urlencode()