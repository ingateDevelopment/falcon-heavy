from __future__ import unicode_literals, absolute_import

import os
import decimal
from contextlib import contextmanager

from six import string_types, integer_types
from six.moves.urllib_parse import urlparse, urldefrag

from .compat import Mapping, MutableMapping
from .utils import read_yaml_file
from .resolver import RefResolver
from .exceptions import WalkingError, UnresolvableRecursiveReference
from .undefined import Undefined


DEFAULT_RESOLVER_HANDLERS = {
    'file': lambda uri: read_yaml_file(urlparse(uri, 'file').path),
}


class Cursor(object):

    """Object for walking by document.

    :param base_uri: Base uri of document. Absolute path for example.
    :param document: Document instance.
    :param resolver_handlers: Handlers for references resolving.
        Default: None.
    """

    __slots__ = [
        '_value',
        '_resolver',
        '_visited_refs'
    ]

    def __init__(self, base_uri, document, resolver_handlers=None):
        self._value = document
        handlers = resolver_handlers or DEFAULT_RESOLVER_HANDLERS
        self._resolver = RefResolver(base_uri, document, handlers=handlers)
        self._visited_refs = set()

    @contextmanager
    def walk(self, part, default=Undefined):
        """Walking by nested structures.

        :param part: List index or dictionary key.
        :param default: The value that will returns if the part with
            the corresponding index or key is not found.
        """
        with self.in_scope(part):
            self._visited_refs.clear()
            old_value = self._value
            try:
                if self.is_mapping or self.is_array:
                    try:
                        self._value = self._value[part]
                    except (KeyError, IndexError):
                        self._value = default
                    yield
                else:
                    raise WalkingError("Couldn't walk into")
            finally:
                self._value = old_value

    @contextmanager
    def walk_ref(self, ref):
        """Walking by references.

        :param ref: Reference.
        """
        with self._resolver.resolving(ref) as target:
            resolution_scope = self._resolver.resolution_scope
            if resolution_scope in self._visited_refs:
                raise UnresolvableRecursiveReference(
                    "Unresolvable recursive reference {}".format(ref))
            self._visited_refs.add(resolution_scope)
            old_value, self._value = self._value, target
            try:
                yield
            finally:
                self._value = old_value
                self._visited_refs.discard(resolution_scope)

    @contextmanager
    def in_scope(self, part):
        _, fragment = urldefrag(self._resolver.resolution_scope)
        fragment = '#{}/{}'.format(fragment, str(part).replace('~', '~0').replace('/', '~1'))
        with self._resolver.in_scope(fragment):
            yield

    @property
    def is_ref(self):
        return self.is_mapping and '$ref' in self.value

    @property
    def is_mapping(self):
        return isinstance(self.value, (Mapping, MutableMapping))

    @property
    def is_array(self):
        return isinstance(self.value, (list, tuple))

    @property
    def is_string(self):
        return isinstance(self.value, string_types)

    @property
    def is_boolean(self):
        return isinstance(self.value, bool)

    @property
    def is_integer(self):
        return isinstance(self.value, integer_types)

    @property
    def is_number(self):
        return isinstance(self.value, integer_types + (float, decimal.Decimal))

    @property
    def is_bytes(self):
        return isinstance(self.value, bytes)

    @property
    def is_null(self):
        return self.value is None

    @property
    def is_undefined(self):
        return self.value is Undefined

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v

    @property
    def url(self):
        return self._resolver.resolution_scope

    @classmethod
    def from_file(cls, path, resolver_handlers=None):
        spec = read_yaml_file(path)
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        base_uri = 'file://{}'.format(path)
        return cls(base_uri, spec, resolver_handlers=resolver_handlers)

    @classmethod
    def from_raw(cls, raw, resolver_handlers=None):
        return cls('', raw, resolver_handlers=resolver_handlers)
