from __future__ import unicode_literals

from ..schema import types

from .registry import registered, hashkey


class RequestBodyFactory(object):

    def __init__(self, content_factory):
        self.content_factory = content_factory

    @registered(key=lambda request_body: hashkey(request_body.path))
    def generate(self, request_body):
        return types.ObjectType(
            additional_properties=False,
            properties={
                'content':
                    types.AnyType() if request_body is None else self.content_factory.generate(request_body['content'])
            },
            required={'content'} if request_body is not None and request_body['required'] else None
        )
