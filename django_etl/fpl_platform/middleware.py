"""Project middleware."""
from django.middleware.gzip import GZipMiddleware


class ApiGZipMiddleware(GZipMiddleware):
    """Compress JSON API responses only.

    The Stats Explorer payload is ~475 KB of JSON and compresses about 6x.
    HTML pages are left alone: compressing pages that carry secrets (CSRF
    tokens) alongside reflected input is what the BREACH attack exploits,
    and WhiteNoise already serves pre-compressed static files.
    """

    def process_response(self, request, response):
        if not request.path.startswith("/api/"):
            return response
        return super().process_response(request, response)
