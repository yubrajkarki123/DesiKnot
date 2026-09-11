from django.apps import AppConfig

class DesiknotAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'DesiKnot_App'

    def ready(self):
        import DesiKnot_App.signals