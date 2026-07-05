# core/celery.py
import os
from celery import Celery

# Establece el módulo de configuración de Django predeterminado para 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Usamos una cadena aquí para que el worker no tenga que serializar
# el objeto de configuración en los procesos hijos.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carga automáticamente las tareas (tasks.py) de todas las aplicaciones registradas.
app.autodiscover_tasks()