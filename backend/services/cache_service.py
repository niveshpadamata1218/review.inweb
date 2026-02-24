"""
Simple in-memory cache service.
Replace with Redis in production.
"""

from cachelib import SimpleCache

cache = SimpleCache()


def get_cached(key):
    return cache.get(key)


def set_cached(key, value, timeout=3600):
    cache.set(key, value, timeout=timeout)


def invalidate_cache(key):
    cache.delete(key)
