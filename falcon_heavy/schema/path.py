from __future__ import unicode_literals

from six import PY3, string_types, text_type
from six.moves.urllib_parse import urldefrag

from .._compat import lru_cache


_urldefrag_cache = lru_cache(1024)(urldefrag)


def _escape(s):
    return s.replace('~', '~0').replace('/', '~1')


class Path(object):

    __slots__ = [
        '_url',
        '_parts'
    ]

    def __new__(cls, uri):
        return cls._from_uri(uri)

    @classmethod
    def _from_uri(cls, uri):
        self = object.__new__(cls)
        url, fragment = _urldefrag_cache(uri)
        self._url = url
        self._parts = tuple(filter(None, fragment.split('/')))
        return self

    @classmethod
    def _from_parsed_parts(cls, url, parts):
        self = object.__new__(cls)
        self._url = url
        self._parts = parts
        return self

    def _make_child(self, part):
        return self._from_parsed_parts(self._url, self._parts + (part, ))

    @property
    def parent(self):
        if not self._parts:
            return self
        return self._from_parsed_parts(self._url, self._parts[:-1])

    @property
    def parts(self):
        return tuple(self._parts)

    @property
    def url(self):
        return self._url

    def __div__(self, part):
        if isinstance(part, int):
            part = text_type(part)
        elif not isinstance(part, string_types):
            raise NotImplemented

        return self._make_child(part)

    __truediv__ = __div__

    def __eq__(self, other):
        if isinstance(other, string_types):
            return str(self) == other
        elif isinstance(other, Path):
            return self.url == other.url and self.parts == other.parts
        else:
            raise NotImplemented

    def __hash__(self):
        return hash(text_type(self))

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        fragment = '/'.join(map(_escape, self._parts))

        if fragment:
            return '#/'.join((self._url, fragment))
        elif self._url:
            return self._url
        else:
            return '#'

    if PY3:
        __str__ = __unicode__

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, text_type(self))
