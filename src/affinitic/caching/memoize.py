from zope.app.cache import ram

from plone.memoize import volatile
from plone.memoize.ram import cache as ram_cache
from plone.memoize.ram import RAMCacheAdapter


def one_day_memoize_for_instances(fun):
    """
    Use this to decorate class instances methods only
    Cached return values are cleared every day
    """

    def get_key(fun, *arg, **kwargs):
        # remove 'self' attribute received from instance method
        return (arg[1:], frozenset(kwargs.items()), )

    return ram_cache(get_key)(fun)


one_hour_global_cache = ram.RAMCache()
one_hour_global_cache.update(maxAge=3600)


def one_hour_memoize_for_instances(fun):
    """
    Use this to decorate class instances methods only
    Cached return values are cleared every hour
    """

    def store_in_cache(fun, *args, **kwargs):
        key = '%s.%s' % (fun.__module__, fun.__name__)
        return RAMCacheAdapter(one_hour_global_cache, globalkey=key)

    def get_key(fun, *arg, **kwargs):
        # remove 'self' attribute received from instance method
        return (arg[1:], frozenset(kwargs.items()), )

    def cache(get_key):
        return volatile.cache(get_key, get_cache=store_in_cache)

    return cache(get_key)(fun)
