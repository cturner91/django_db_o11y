import os

from django.core.asgi import get_asgi_application


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_db_o11y.settings')
application = get_asgi_application()
