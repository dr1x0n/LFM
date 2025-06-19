from django.apps import AppConfig
import os

class LFMAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    path = os.path.dirname(os.path.abspath(__file__)) 