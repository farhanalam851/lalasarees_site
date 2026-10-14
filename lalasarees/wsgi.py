import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lalasarees.settings")


def missing_settings():
    from django.conf import settings
    problems = []
    if not settings.DEBUG and settings.SECRET_KEY == settings.INSECURE_DEFAULT_KEY:
        problems.append("DJANGO_SECRET_KEY is not set")
    if settings.ON_VERCEL and not settings.DATABASE_URL:
        problems.append("DATABASE_URL is not set")
    return problems


_problems = missing_settings()
if _problems:
    # Show a readable message instead of Vercel's generic FUNCTION_INVOCATION_FAILED page.
    _msg = ("Deployment settings missing: " + "; ".join(_problems) +
            ". Add them in Vercel > Settings > Environment Variables (Production), then redeploy.\n").encode()
    print(_msg.decode())

    def application(environ, start_response):
        start_response("500 Internal Server Error", [("Content-Type", "text/plain; charset=utf-8"),
                                                     ("Content-Length", str(len(_msg)))])
        return [_msg]
else:
    application = get_wsgi_application()
