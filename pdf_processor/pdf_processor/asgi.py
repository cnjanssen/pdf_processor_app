# pdf_processor/asgi.py
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pdf_processor.settings')

application = get_asgi_application()