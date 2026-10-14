from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class CanonicalHostMiddleware:
    """One-hop 301 to https://CANONICAL_HOST so http, www and non-www never chain.

    Without this, http://example.com -> https://example.com -> https://www.example.com is two redirects.
    Active only when DEBUG is off and DJANGO_CANONICAL_HOST is set. Health checks on localhost are left alone.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = getattr(settings, "CANONICAL_HOST", "")
        if host and not settings.DEBUG:
            req_host = request.get_host().split(":")[0]
            https = request.headers.get("X-Forwarded-Proto", request.scheme) == "https"
            if req_host not in ("localhost", "127.0.0.1") and (req_host != host or not https):
                return HttpResponsePermanentRedirect(f"https://{host}{request.get_full_path()}")
        return self.get_response(request)
