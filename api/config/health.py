from django.http import HttpResponse

from config.health import health


class HealthCheckMiddleware:
    """Answers health probes before host validation and the HTTPS redirect run.

    /healthz: plain liveness for probes that hit the container directly.
    /api/health: Savannaa's readiness check, with database/Redis/worker status.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/healthz":
            return HttpResponse("ok", content_type="text/plain")
        if request.path == "/api/health":
            return health(request)
        return self.get_response(request)