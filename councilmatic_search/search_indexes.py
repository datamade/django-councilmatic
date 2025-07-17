import re

from django.utils.html import strip_tags
from haystack import indexes

from councilmatic_core.models import Bill


class BillIndex(indexes.SearchIndex):
    identifier = indexes.CharField(model_attr="identifier", boost=2)
    title = indexes.CharField(model_attr="title", boost=1.25)
    abstract = indexes.CharField(
        model_attr="abstracts__abstract", boost=1.25, default=""
    )
    text = indexes.CharField(
        document=True,
        use_template=True,
        template_name="councilmatic_search/templates/indexes/bill_text.txt",
    )
    full_text = indexes.CharField(model_attr="full_text", default="")

    def get_model(self):
        return Bill

    def prepare_full_text(self, obj):
        sanitized_value = strip_tags(obj.full_text).replace("\n", "")
        return re.sub(r"&(?:\w+|#\d+);", "", sanitized_value)
