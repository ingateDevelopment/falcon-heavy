from __future__ import unicode_literals

import weakref
from functools import wraps

from .types import ProxyType


kwd_mark = (object(),)


def hashkey(*args, **kwargs):
    """Return a cache key for the specified hashable arguments"""

    key = args
    if kwargs:
        key += kwd_mark + tuple(sorted(kwargs.items()))

    return key


def registered(key=hashkey):
    """Registered decorator

    Stores generated types in the registry. Allow recursive generation
    """

    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            k = key(*args, **kwargs)
            try:
                registry = self.__registry
            except AttributeError:
                registry = self.__registry = {}
            result = registry.get(k)
            if result is not None:
                return result
            proxy = ProxyType()
            registry[k] = proxy
            result = method(self, *args, **kwargs)
            proxy.wrapped = weakref.proxy(result)
            registry[k] = result
            return result
        return wrapper
    return decorator
