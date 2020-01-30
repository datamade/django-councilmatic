from haystack import indexes

from councilmatic_core.models import Bill
from councilmatic_core.templatetags.extras import clean_html


class BillIndex(indexes.SearchIndex):

    text = indexes.CharField(document=True,
                             use_template=True,
                             template_name='search/indexes/councilmatic_core/bill_text.txt')
    slug = indexes.CharField(model_attr='slug', indexed=False)
    id = indexes.CharField(model_attr='id', indexed=False)
    bill_type = indexes.CharField(faceted=True)
    identifier = indexes.CharField(model_attr='identifier')
    description = indexes.CharField(model_attr='title', boost=1.25)
    source_url = indexes.CharField(model_attr='sources__url', indexed=False)
    source_note = indexes.CharField(model_attr='sources__note')
    abstract = indexes.CharField(model_attr='abstracts__abstract', boost=1.25, default='')

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

    def prepare_inferred_status(self, obj):
        return obj.inferred_status

    def prepare_legislative_session(self, obj):
        return obj.legislative_session.identifier

    def prepare_ocr_full_text(self, obj):
        return clean_html(obj.ocr_full_text)

    def get_updated_field(self):
        return 'updated_at'

    def prepare_last_action_date(self, obj):
        # Solr seems to be fussy about the time format, and we do not need the time, just the date stamp.
        # https://lucene.apache.org/solr/guide/7_5/working-with-dates.html#date-formatting
        if obj.last_action_date:
            return obj.last_action_date.date()
