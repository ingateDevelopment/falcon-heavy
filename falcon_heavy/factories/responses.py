from __future__ import unicode_literals

from six import iteritems

from ..schema import types

from .types import ResponseCodeBestMatchedType
from .properties import PropertyFactory, PROPERTY_GENERATION_MODE
from .content import ContentFactory
from .media_type import ResponseMediaTypeFactory
from .parameters import ParameterFactory
from .headers import HeadersFactory
from .registry import registered, hashkey


class ResponseFactory(object):

    def __init__(self, content_factory, headers_factory):
        self.content_factory = content_factory
        self.headers_factory = headers_factory

    @registered(key=lambda response: hashkey(response.path))
    def generate(self, response):
        content = response.get('content')
        headers = response.get('headers')

        return types.ObjectType(
            properties={
                'content': types.AnyType() if content is None else self.content_factory.generate(content),
                'headers': types.AnyType() if headers is None else self.headers_factory.generate(headers)
            },
            additional_properties=False
        )


class ResponsesFactory(object):

    def __init__(self):
        self.property_factory = PropertyFactory(mode=PROPERTY_GENERATION_MODE.READ_ONLY)
        self.media_type_factory = ResponseMediaTypeFactory(self.property_factory)
        self.content_factory = ContentFactory(self.media_type_factory)
        self.parameter_factory = ParameterFactory(self.property_factory)
        self.headers_factory = HeadersFactory(self.parameter_factory)
        self.response_factory = ResponseFactory(self.content_factory, self.headers_factory)

    def generate(self, responses):
        return ResponseCodeBestMatchedType(
            supported={code: self.response_factory.generate(response) for code, response in iteritems(responses)}
        )
