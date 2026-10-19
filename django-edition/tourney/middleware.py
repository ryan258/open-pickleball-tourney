from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.utils.datastructures import MultiValueDictKeyError
from .engine import DomainError


class BoundaryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if not request.path.startswith("/static/"):
            response["Cache-Control"] = "private, no-store"
        return response

    def process_exception(self, request, exc):
        if isinstance(exc, DomainError):
            accept = request.headers.get("Accept", "")
            if "application/json" in accept and "text/html" not in accept:
                return JsonResponse({"error": exc.code, "message": str(exc)}, status=exc.status)
            return render(request, "error.html", {"message": str(exc), "code": exc.code}, status=exc.status)
        if isinstance(exc, (ValidationError, MultiValueDictKeyError)):
            return render(request, "error.html", {"message": "That input is not valid. Review it and try again.", "code": "invalid"}, status=400)

