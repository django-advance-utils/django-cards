from django.apps import AppConfig


class ModalConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'cards'
    verbose_name = 'Cards'

    def ready(self):
        from cards.render_scope import connect_signals
        connect_signals()
