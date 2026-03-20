# apps.py
from django.apps import AppConfig

class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'  # This should match your app folder name (lowercase)
    
    def ready(self):
        import main.signals  # This should match your app folder name (lowercase)