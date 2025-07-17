from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail.admin.panels import FieldPanel

from .blocks import ArticleBlock


class StaticPage(Page):
    include_in_dump = True

    body = StreamField(
        [
            ("section", ArticleBlock()),
        ],
        use_json_field=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]
