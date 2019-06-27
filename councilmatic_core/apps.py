from django.apps import AppConfig


class CouncilmaticConfig(AppConfig):
    name = 'councilmatic_core'
    verbose_name = "Councilmatic"

    def ready(self):
        import councilmatic_core.signals.handlers  # noqa
