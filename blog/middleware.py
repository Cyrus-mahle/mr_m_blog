"""Adds security headers to every response."""
from django.conf import settings
from django.utils.cache import patch_cache_control


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Content Security Policy: the browser may only load things from our own site.
        # The Django admin uses a few inline styles, so it gets a slightly softer rule.
        in_admin = request.path.startswith("/" + settings.ADMIN_URL)
        style_src = "style-src 'self' 'unsafe-inline'" if in_admin else "style-src 'self'"
        csp = "; ".join(
            [
                "default-src 'self'",
                "script-src 'self'",
                style_src,
                "img-src 'self' data:",
                "font-src 'self'",
                "connect-src 'self'",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
            ]
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")

        # Pages for logged-in users must never be stored by shared caches.
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            patch_cache_control(response, private=True, no_cache=True, no_store=True)
        return response