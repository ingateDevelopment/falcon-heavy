from __future__ import unicode_literals

from ..schema import types

from .properties import PropertyFactory, PROPERTY_GENERATION_MODE
from .parameters import ParameterFactory, ParametersFactory
from .headers import HeadersFactory
from .media_type import RequestMediaTypeFactory
from .content import ContentFactory
from .request_body import RequestBodyFactory


class RequestFactory(object):

    def __init__(self):
        self.property_factory = PropertyFactory(mode=PROPERTY_GENERATION_MODE.WRITE_ONLY)
        self.parameter_factory = ParameterFactory(self.property_factory)
        self.parameters_factory = ParametersFactory(self.parameter_factory)
        self.headers_factory = HeadersFactory(self.parameter_factory)
        self.media_type_factory = RequestMediaTypeFactory(self.property_factory, self.headers_factory)
        self.content_factory = ContentFactory(self.media_type_factory)
        self.request_body_factory = RequestBodyFactory(self.content_factory)

    def generate(self, parameters=None, request_body=None):
        return types.ObjectType(
            additional_properties=False,
            properties={
                'parameters':
                    types.AnyType() if parameters is None else self.parameters_factory.generate(parameters),
                'body':
                    types.AnyType() if request_body is None else self.request_body_factory.generate(request_body)
            }
        )
