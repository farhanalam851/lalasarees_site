import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lalasarees.settings")

from lalasarees.settings import validate_production  # noqa: E402

validate_production()
application = get_wsgi_application()
