"""Small helpers that slow down attackers (rate limiting)."""
import hashlib

from django.conf import settings
from django.core.cache import cache


def client_ip(request):
    if settings.USE_X_REAL_IP:
        ip = request.META.get("HTTP_X_REAL_IP")
        if ip:
            return ip.strip()[:45]
    return request.META.get("REMOTE_ADDR", "unknown")


def throttle_key(scope, *parts):
    raw = "|".join([scope, *[str(p) for p in parts]])
    return "thr:" + hashlib.sha256(raw.encode()).hexdigest()


def hit(key, window_seconds):
    """Count one attempt. The counter disappears after window_seconds."""
    if cache.add(key, 1, window_seconds):
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, window_seconds)
        return 1


def over_limit(key, limit):
    return (cache.get(key) or 0) >= limit


def reset(key):
    cache.delete(key)