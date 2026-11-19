from django.http import HttpResponse


class HealthCheckMiddleware:
    """Answers /healthz before host validation and the HTTPS redirect run.

    Platform health probes hit the container directly — plain HTTP, no X-Forwarded-Proto, and a
    Host header (pod IP) that isn't in ALLOWED_HOSTS — so routing them through the normal stack
    would return a 301 or 400 instead of 200.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/healthz":
            return HttpResponse("ok", content_type="text/plain")
        return self.get_response(request)
