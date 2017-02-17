from councilmatic_core.models import Bill
from haystack import indexes
from councilmatic_core.templatetags.extras import clean_html

# XXX: is it OK to link to Django settings in haystack_indexes.py ?
from django.conf import settings
import pytz
app_timezone = pytz.timezone(settings.TIME_ZONE)


class BillIndex(indexes.SearchIndex):

    text = indexes.CharField(document=True, use_template=True,
                             template_name="search/indexes/councilmatic_core/bill_text.txt")
    slug = indexes.CharField(model_attr='slug', indexed=False)
    ocd_id = indexes.CharField(model_attr='ocd_id', indexed=False)
    bill_type = indexes.CharField(faceted=True)
    identifier = indexes.CharField(model_attr='identifier')
    description = indexes.CharField(model_attr='description', boost=1.25)
    source_url = indexes.CharField(model_attr='source_url', indexed=False)
    source_note = indexes.CharField(model_attr='source_note')
    abstract = indexes.CharField(model_attr='abstract', boost=1.25, default='')

    friendly_name = indexes.CharField()
    sort_name = indexes.CharField()
    sponsorships = indexes.MultiValueField(faceted=True)
    actions = indexes.MultiValueField()
    controlling_body = indexes.MultiValueField(faceted=True)
    full_text = indexes.CharField(model_attr='full_text', default='')
    ocr_full_text = indexes.CharField(model_attr='ocr_full_text', default='')
    last_action_date = indexes.DateTimeField()
    inferred_status = indexes.CharField(faceted=True)
    legislative_session = indexes.CharField(faceted=True)

    def get_model(self):
        return Bill

    def prepare_friendly_name(self, obj):
        return obj.friendly_name

    def prepare_sort_name(self, obj):
        return obj.friendly_name.replace(" ", "")

    def prepare_bill_type(self, obj):
        return obj.bill_type.lower()

    def prepare_sponsorships(self, obj):
        return [sponsorship.person for sponsorship in obj.sponsorships.all()]

    def prepare_actions(self, obj):
        return [action for action in obj.actions.all()]

    def prepare_controlling_body(self, obj):
        if obj.controlling_body:
            return [org.name for org in obj.controlling_body]

    def prepare_full_text(self, obj):
        return clean_html(obj.full_text)

    def prepare_last_action_date(self, obj):
        from datetime import datetime, timedelta
        if not obj.last_action_date:
            return datetime.now().replace(tzinfo=app_timezone) - timedelta(days=36500)
        return obj.last_action_date

    def prepare_inferred_status(self, obj):
        return obj.inferred_status

    def prepare_legislative_session(self, obj):
        return obj._legislative_session.identifier

    def prepare_ocr_full_text(self, obj):
        return clean_html(obj.ocr_full_text)

    def get_updated_field(self):
        return 'updated_at'
