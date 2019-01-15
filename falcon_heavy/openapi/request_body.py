from __future__ import unicode_literals

from wrapt import ObjectProxy

from ..schema import types

from .base import BaseOpenApiObjectType
from .media_type import MediaTypeObjectType, ContentMapType


class RequestBodyObjectProxy(ObjectProxy):

    __slots__ = [
        '_self_path'
    ]

    def __init__(self, wrapped, path):
        super(RequestBodyObjectProxy, self).__init__(wrapped)
        self._self_path = path

    @property
    def path(self):
        return self._self_path

    @path.setter
    def path(self, value):
        self._self_path = value


class RequestBodyObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'description': types.StringType(),
        'content': ContentMapType(MediaTypeObjectType()),
        'required': types.BooleanType(default=False)
    }

    REQUIRED = {
        'content'
    }

    def _convert(self, raw, path, **context):
        converted = super(RequestBodyObjectType, self)._convert(raw, path, **context)

        return RequestBodyObjectProxy(converted, path)
