from __future__ import unicode_literals

import os

import yaml

import falcon
from falcon import media

from six import iteritems
from six.moves.urllib_parse import urljoin

from .schema.path import Path
from .schema.ref_resolver import RefResolver
from .factories import (
    RequestFactory,
    ResponsesFactory
)
from .openapi import OpenApiObjectType
from .request import FalconHeavyRequest, FalconHeavyRequestOptions
from .response import FalconHeavyResponse
from .media_handlers.json_handler import FalconHeavyJSONHandler
from .middleware import ValidationMiddleware
from .exceptions import FalconHeavyHTTPError
from . import logger


class FalconHeavyApi(falcon.API):

    """API providing type casting and validation of requests and responses
    according to the OpenApi specification.

    :param specification_path: Path to specification.
    :param resource_resolver: Falcon resources resolver.
    """

    __slots__ = []

    @staticmethod
    def load_specification(path, handlers=()):
        """Loads specification from file

        :param path: path to file
        :type path: basestring
        :param handlers: handlers for references resolver
        :type handlers: dict of callable
        :return: OpenAPI object
        :rtype: Object
        """
        with open(path) as fh:
            referrer = yaml.safe_load(fh)
        path = os.path.abspath(path)
        base_uri = urljoin('file://', path)
        return OpenApiObjectType().convert(
            referrer,
            Path(base_uri),
            strict=True,
            registry={},
            ref_resolver=RefResolver(base_uri, referrer, handlers=handlers)
        )

    def __init__(self, specification_path, resource_resolver,
                 request_type=FalconHeavyRequest, response_type=FalconHeavyResponse,
                 middleware=None, **kwargs):
        specification = self.load_specification(specification_path)

        if middleware is None:
            middleware = []

        middleware.append(ValidationMiddleware())

        assert issubclass(request_type, FalconHeavyRequest), (
            "Request type must be subclass of `FalconHeavyRequest`")

        assert issubclass(response_type, FalconHeavyResponse), (
            "Response type must be subclass of `FalconHeavyResponse`")

        super(FalconHeavyApi, self).__init__(
            middleware=middleware,
            request_type=request_type,
            response_type=response_type,
            **kwargs
        )

        self.req_options = FalconHeavyRequestOptions()

        self.req_options.keep_blank_qs_values = True
        self.req_options.auto_parse_qs_csv = False
        self.req_options.auto_parse_form_urlencoded = False

        self.add_error_handler(FalconHeavyHTTPError)

        # Replace standard media handlers in the responses to serialize
        # according to the specification
        self.resp_options.media_handlers = media.Handlers({
            'application/json': FalconHeavyJSONHandler(),
            'application/json; charset=UTF-8': FalconHeavyJSONHandler(),
        })

        request_factory = RequestFactory()
        responses_factory = ResponsesFactory()

        for uri_template, path_item in iteritems(specification['paths']):
            resource_id = path_item['x-resource']
            lazy = resource_resolver.resolve(resource_id)

            if lazy is None:
                logger.error(
                    "Resource `%s` is not resolved. Skip path `%s`", resource_id, uri_template)
                continue

            assert callable(lazy), "Resource '{}' must be resolved as callable".format(resource_id)

            operation_schemas = {}
            for http_method in falcon.HTTP_METHODS:
                operation = path_item.get(http_method.lower())
                if operation is None:
                    continue

                operation_schema = operation_schemas.setdefault(http_method, {})

                operation_schema['request'] = request_factory.generate(
                    parameters=operation.get('parameters'),
                    request_body=operation.get('requestBody')
                )

                operation_schema['responses'] = responses_factory.generate(operation['responses'])

                operation_schema['security'] = operation.get('security')

            resource = lazy()
            assert resource, "Resource '{}' is not instantiated".format(resource_id)

            setattr(resource, '__operation_schemas', operation_schemas)
            self.add_route(uri_template, resource)
