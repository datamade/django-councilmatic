from django.apps import AppConfig


class CouncilmaticConfig(AppConfig):
    name = "councilmatic_core"
    verbose_name = "Councilmatic"

    def ready(self):
        import councilmatic_core.signals.handlers  # noqa

        # Check if optional modules are available and configure them
        self._setup_search_integration()
        self._setup_cms_integration()

    def _setup_search_integration(self):
        try:
            from django.apps import apps

            if apps.is_installed("councilmatic_search"):
                # Register search indexes automatically
                from councilmatic_search import search_indexes  # noqa

                print("Legislative search integration enabled")
        except ImportError:
            pass

    def _setup_cms_integration(self):
        try:
            from django.apps import apps

            if apps.is_installed("councilmatic_cms"):
                # Auto-register Wagtail hooks or page types
                from councilmatic_cms import wagtail_hooks  # noqa

                print("Legislative CMS integration enabled")
        except ImportError:
            pass
