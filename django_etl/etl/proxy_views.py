import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.cache import cache_page

@require_GET
@cache_page(60 * 60 * 24)  # Cache for 24 hours
def proxy_image(request):
    """
    Proxy an image URL to bypass CORS restrictions.
    """
    url = request.GET.get('url')
    if not url:
        return JsonResponse({"error": "Missing url parameter"}, status=400)
    
    # Validate URL domain to prevent open proxy abuse
    allowed_domains = ['fantasy.premierleague.com', 'resources.premierleague.com']
    if not any(domain in url for domain in allowed_domains):
        return JsonResponse({"error": "Domain not allowed"}, status=403)

    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', 'image/png')
        
        django_response = HttpResponse(response.content, content_type=content_type)
        django_response['Access-Control-Allow-Origin'] = '*'
        django_response['Cache-Control'] = 'public, max-age=86400'
        
        return django_response
        
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=502)
