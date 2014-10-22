# -*- coding: utf-8 -*-
"""
affinitic.caching

Licensed under the GPL license, see LICENCE.txt for more details.
Copyright by Affinitic sprl

$Id: event.py 67630 2006-04-27 00:54:03Z jfroche $
"""
import cPickle
import md5
import os
import pkg_resources

try:
    pkg_resources.get_distribution('sqlalchemy')
except pkg_resources.DistributionNotFound:

    class RowProxy(object):
        pass
else:  # we have sqlalchemy
    try:
        from sqlalchemy.engine.base import RowProxy
    except ImportError, e:
        from sqlalchemy.engine import RowProxy


from lovely.memcached.event import InvalidateCacheEvent
from lovely.memcached.interfaces import IMemcachedClient
from lovely.memcached.utility import MemcachedClient

from zope import event
from zope.component import queryUtility
from zope.ramcache.interfaces.ram import IRAMCache

from plone.memoize import volatile
from plone.memoize.interfaces import ICacheChooser
from plone.memoize.ram import (AbstractDict, store_in_cache, RAMCacheAdapter)

from affinitic.caching.interfaces import IMemcachedDefaultNameSpace

DEPENDENCIES = {}


class MemcachedClientWithNameSpace(MemcachedClient):
    """
    Delegate the namespace definition to a utility
    Cache the namespace calculation
    """
    _defaultNS = None

    @property
    def defaultNS(self):
        if self._defaultNS is not None:
            return self._defaultNS
        defaultNameSpace = queryUtility(IMemcachedDefaultNameSpace)
        if defaultNameSpace is not None:
            defaultNameSpace = defaultNameSpace()
            if defaultNameSpace is not None:
                self._defaultNS = defaultNameSpace

    def _getNS(self, ns, raw):
        defaultNameSpace = self.defaultNS or 'defaultNS'
        if not ns and defaultNameSpace:
            if raw:
                ns = str(defaultNameSpace)
            else:
                ns = defaultNameSpace
        return ns or None


def memcachedClient():
    servers = os.environ.get("MEMCACHE_SERVER", "127.0.0.1:11211").split(",")
    return MemcachedClientWithNameSpace(servers, defaultNS=None,
                                        defaultAge=86400)


class MemcacheAdapter(AbstractDict):

    def __init__(self, client, globalkey=''):
        self.client = client

        dependencies = []
        if globalkey:
            for k, v in DEPENDENCIES.items():
                dependencies.append(k)

        self.dependencies = dependencies

    def _make_key(self, source):
        return md5.new(source).hexdigest()

    def __getitem__(self, key):
        cached_value = self.client.query(self._make_key(key), raw=True)
        if cached_value is None:
            raise KeyError(key)
        else:
            return cPickle.loads(cached_value)

    def __setitem__(self, key, value):
        try:
            cached_value = cPickle.dumps(value)
        except TypeError:
            if isinstance(value, list) and isinstance(value[0], RowProxy):
                value = [dict(d) for d in value]
            elif isinstance(value, RowProxy):
                value = dict(value)
            else:
                raise
            cached_value = cPickle.dumps(value)
        self.client.set(cached_value, self._make_key(key), raw=True,
                        dependencies=self.dependencies)

    def setWithLifetime(self, key, value, lifetime):
        cached_value = cPickle.dumps(value)
        self.client.set(cached_value, self._make_key(key), raw=True,
                        lifetime=lifetime,
                        dependencies=self.dependencies)


def choose_cache(fun_name):
    client = queryUtility(IMemcachedClient)
    if client is not None:
        return MemcacheAdapter(client, globalkey=fun_name)
    else:
        return RAMCacheAdapter(queryUtility(IRAMCache),
                               globalkey=fun_name)


_marker = object()


def cache(get_key, dependencies=None, get_dependencies=None, lifetime=None):

    def decorator(fun):

        def replacement(*args, **kwargs):
            try:
                key = get_key(fun, *args, **kwargs)
            except volatile.DontCache:
                return fun(*args, **kwargs)
            key = str(key)

            # Do not cache when not using memcache with dependencies
            memcache_client = queryUtility(IMemcachedClient)
            if (dependencies is not None or get_dependencies is not None) and not memcache_client:
                return fun(*args, **kwargs)

            if dependencies is not None or get_dependencies is not None:
                deps = dependencies
                if get_dependencies is not None:
                    deps = get_dependencies(fun, *args, **kwargs)
                for d in deps:
                    new_deps = DEPENDENCIES.get(d, [])
                    if key not in new_deps:
                        new_deps.append(key)
                        DEPENDENCIES[d] = new_deps
            cache = store_in_cache(fun, *args, **kwargs)
            cached_value = cache.get(key, _marker)
            if cached_value is _marker:
                if lifetime is None:
                    cached_value = cache[key] = fun(*args, **kwargs)
                else:
                    cached_value = fun(*args, **kwargs)
                    cache.setWithLifetime(key, cached_value, lifetime)
            return cached_value
        return replacement
    return decorator


def invalidate_key(funcname, key):
    client = queryUtility(IMemcachedClient)
    cache = queryUtility(ICacheChooser)(key)
    if client is not None:
        invalidateEvent = InvalidateCacheEvent(key=cache._make_key(key),
                                               raw=True)
        event.notify(invalidateEvent)
    else:
        key = dict(key=cache._make_key(key))
        cache.ramcache.invalidate(funcname, key=key)


def invalidate_dependencies(dependencies):
    """
    Invalidate all caches linked to dependencies
    """
    client = queryUtility(IMemcachedClient)
    # memcached
    if client is not None:
        invalidateEvent = InvalidateCacheEvent(raw=True,
                                               dependencies=dependencies)
        event.notify(invalidateEvent)
    # ramcache
    else:
        # Cannot invalidate dependencies with ramcache
        pass
