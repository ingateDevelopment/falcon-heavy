from __future__ import unicode_literals

from six import iteritems

from mimeparse import best_match

from .._compat import Mapping

from ..schema import types
from ..schema.exceptions import SchemaError, Error


class ProxyType(types.AbstractConvertible):

    __slots__ = ['wrapped']

    def __init__(self, wrapped=None, **kwargs):
        self.wrapped = wrapped
        super(ProxyType, self).__init__(**kwargs)

    def convert(self, raw, path, **context):
        assert self.wrapped is not None, "Wrapped type must be specified"

        return self.wrapped.convert(raw, path, **context)


class AbstractBestMatchedType(types.AbstractType):

    MESSAGES = {
        'improper': "Must be a mapping that contains only one entry",
        'unexpected': "Unexpected value"
    }

    __slots__ = ['supported']

    def __init__(self, supported, **kwargs):
        super(AbstractBestMatchedType, self).__init__(**kwargs)
        self.supported = supported

    def _best_match(self, value):
        raise NotImplementedError

    def _convert(self, raw, path, **context):
        if not isinstance(raw, Mapping) or len(raw) != 1:
            raise SchemaError(Error(path, self.messages['improper']))

        k, v = list(raw.items())[0]
        best_matched = self._best_match(k)

        if best_matched is None:
            raise SchemaError(Error(path / k, self.messages['unexpected']))

        return best_matched.convert(v, path / k, **context)


class ContentTypeBestMatchedType(AbstractBestMatchedType):

    MESSAGES = {
        'unexpected': "Unexpected content-type"
    }

    __slots__ = []

    def _best_match(self, value):
        best_matched = self.supported.get(value)

        if best_matched is None:
            matched = best_match(self.supported.keys(), value)
            if matched:
                best_matched = self.supported[matched]

        return best_matched


class ResponseCodeBestMatchedType(AbstractBestMatchedType):

    MESSAGES = {
        'unexpected': "Unexpected response code"
    }

    __slots__ = []

    def __init__(self, supported, **kwargs):
        super(ResponseCodeBestMatchedType, self).__init__(supported, **kwargs)

        # Replace all `X` in code ranges by empty
        self.supported = {
            k.lower().replace('x', ''): v for k, v in iteritems(self.supported)
        }

    def _best_match(self, value):
        default = self.supported.get('default', None)

        best_matched = self.supported.get(value)

        if best_matched is None and value:
            best_matched = self.supported.get(value[0])

        if best_matched is None and default is not None:
            best_matched = default

        return best_matched
