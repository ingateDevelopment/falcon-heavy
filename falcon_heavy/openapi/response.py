from __future__ import unicode_literals

from wrapt import ObjectProxy

from ..schema import types

from .base import BaseOpenApiObjectType
from .types import ReferencedType
from .header import HeaderObjectType
from .media_type import MediaTypeObjectType, ContentMapType
from .link import LinkObjectType


class ResponseObjectProxy(ObjectProxy):

    __slots__ = [
        '_self_path'
    ]

    def __init__(self, wrapped, path):
        super(ResponseObjectProxy, self).__init__(wrapped)
        self._self_path = path

    @property
    def path(self):
        return self._self_path

    @path.setter
    def path(self, value):
        self._self_path = value


class ResponseObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'description': types.StringType(),
        'headers': types.MapType(ReferencedType(HeaderObjectType())),
        'content': ContentMapType(MediaTypeObjectType()),
        'links': types.MapType(ReferencedType(LinkObjectType()))
    }

    REQUIRED = {
        'description'
    }

    def _convert(self, raw, path, **context):
        converted = super(ResponseObjectType, self)._convert(raw, path, **context)

        return ResponseObjectProxy(converted, path)
