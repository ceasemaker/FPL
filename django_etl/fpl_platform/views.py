"""Serve the built React app from the Django process."""
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.cache import never_cache


@never_cache
def spa_index(request):
    """Return frontend/dist/index.html for any non-API route (client-side routing)."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.is_file():
        return HttpResponseNotFound(
            "Frontend bundle not found. Run `npm run build` in frontend/ (build.sh does this on Render).",
            content_type="text/plain",
        )
    # index.html is tiny and changes on every deploy; never let a browser cache it,
    # while the hashed /assets/* files it references are cached by WhiteNoise.
    return HttpResponse(index.read_bytes(), content_type="text/html")
