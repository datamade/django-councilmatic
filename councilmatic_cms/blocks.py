from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.contrib.typed_table_block.blocks import TypedTableBlock


class NavigationBlock(blocks.StaticBlock):
    class Meta:
        template = "lametro/blocks/navigation.html"
        icon = "bars"

    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)

        if parent_context := kwargs.get("parent_context"):
            context["navigation_items"] = {
                section.value["heading"]
                or "Unnamed Section": section.value.get("anchor")
                for section in parent_context["page"].body
                if section.value.get("anchor")
            }

        return context


class Breakpoints(blocks.StructBlock):
    class Meta:
        help_text = "Max number of columns to display on different devices"

    sm = blocks.IntegerBlock(default=1, help_text="Mobile phone")
    md = blocks.IntegerBlock(default=2, help_text="Tablet")
    lg = blocks.IntegerBlock(default=4, help_text="Desktop")


class ResponsiveContent(blocks.StructBlock):
    breakpoints = Breakpoints()
    content = blocks.StreamBlock(
        [
            (
                "table",
                TypedTableBlock(
                    [
                        ("rich_text", blocks.RichTextBlock()),
                    ]
                ),
            )
        ]
    )


class ContentBlock(blocks.StreamBlock):
    text = blocks.RichTextBlock()
    image = ImageChooserBlock()
    table = TypedTableBlock(
        [
            ("rich_text", blocks.RichTextBlock()),
        ]
    )
    navigation = NavigationBlock()
    responsive_element = ResponsiveContent()


class ArticleBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False)
    content = ContentBlock()
    anchor = blocks.CharBlock(
        required=False, help_text="Add anchor to enable direct links to this section"
    )
