from __future__ import absolute_import

import datetime
import importlib
import json
import decimal
from itertools import chain

import rfc3339

import falcon
from falcon import media

import six
from six import iteritems
from six import BytesIO

try:
    from tempfile import SpooledTemporaryFile
except ImportError:
    from tempfile import TemporaryFile
    SpooledTemporaryFile = None

from werkzeug import formparser
from werkzeug.formparser import parse_form_data, MultiPartParser
from werkzeug.exceptions import RequestEntityTooLarge

from .schema.types import Object
from .schema.compat import Mapping
from .openapi.factories import (
    ParametersFactory,
    RequestBodyFactory,
    ResponsesFactory,
)
from .openapi import OpenApi
from .middleware import ValidationMiddleware
from .utils import (
    FormStorage,
    Base64EncodableStream
)
from .errors import (
    FalconHeavyHTTPError,
    FalconHeavyRequestEntityTooLarge,
)
from . import logger


class AbstractResourceResolver(object):

    def resolve(self, resource_id):
        raise NotImplementedError


class RuntimeResourceResolver(AbstractResourceResolver):

    def __init__(self, package):
        self.package = package

    def resolve(self, resource_id):
        parts = resource_id.split(':')

        if len(parts) != 2:
            logger.error(
                "Resource '{}' is not resolved. Invalid resource identifier.".format(resource_id))
            return None

        module_name, attribute_path = parts
        module_name = '{}.{}'.format(self.package, module_name)

        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            logger.error(
                "Resource '{}' is not resolved. Couldn't import module '{}': {}".format(
                    resource_id, module_name, e.message))
            return None

        attribute = module
        for path_item in attribute_path.split('.'):
            try:
                attribute = getattr(attribute, path_item)
            except AttributeError as e:
                logger.error(
                    "Resource '{}' is not resolved. Couldn't find attribute '{}': {}".format(
                        resource_id, attribute_path, e.message))
                return None

        return attribute


class FalconHeavyJsonEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return rfc3339.rfc3339(o)

        elif isinstance(o, datetime.date):
            return o.isoformat()

        elif isinstance(o, decimal.Decimal):
            return str(o)

        elif isinstance(o, Base64EncodableStream):
            chunks = []
            while 1:
                chunk = o.read(64 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)

            return ''.join(chunks)

        return json.JSONEncoder.default(self, o)


class FalconHeavyJSONHandler(media.JSONHandler):

    def serialize(self, obj):
        result = json.dumps(obj, cls=FalconHeavyJsonEncoder, ensure_ascii=False)
        if six.PY3 or not isinstance(result, bytes):
            return result.encode('utf-8')

        return result


class FalconHeavyRequestOptions(falcon.RequestOptions):

    __slots__ = [
        'max_form_memory_size',
        'max_file_memory_size'
    ]

    def __init__(self):
        super(FalconHeavyRequestOptions, self).__init__()
        #: The maximum number of bytes to be accepted for in-memory stored form data.
        # Default: None
        self.max_form_memory_size = None
        #: The maximum size (in bytes) that an upload will be before it gets streamed
        # to the file system. Default: 2621440 (i.e. 2.5 MB).
        self.max_file_memory_size = 2621440


# PR https://github.com/pallets/werkzeug/pull/1290
class FalconHeavyMultiPartParser(MultiPartParser):

    def parse_lines(self, file, boundary, content_length, cap_at_buffer=True):
        for ellt, ell in super(FalconHeavyMultiPartParser, self).parse_lines(
                file, boundary, content_length, cap_at_buffer=cap_at_buffer):
            if ellt == 'begin_form':
                self.headers, _ = ell
            yield ellt, ell

    def parse_parts(self, file, boundary, content_length):
        for part in super(FalconHeavyMultiPartParser, self).parse_parts(
                file, boundary, content_length):
            what, (name, value) = part
            if what == 'form':
                yield (what, (name, FormStorage(value, name, headers=self.headers)))
            else:
                yield part


formparser.MultiPartParser = FalconHeavyMultiPartParser


class FalconHeavyRequest(falcon.Request):

    __slots__ = []

    def _stream_factory(self, total_content_length, filename, content_type, content_length=None):
        if SpooledTemporaryFile is not None:
            return SpooledTemporaryFile(
                max_size=self.options.max_file_memory_size, mode='wb+')

        if (
                total_content_length is None or
                total_content_length > self.options.max_file_memory_size
        ):
            return TemporaryFile('wb+')

        return BytesIO()

    @property
    def media(self):
        if self._media is not None:
            return self._media

        if (
                self.method in ('POST', 'PUT', 'PATCH') and
                any(ct in (self.content_type or '') for ct in (
                    'application/x-www-form-urlencoded',
                    'application/x-url-encoded',
                    'multipart/form-data'
                ))
        ):
            try:
                _, form, files = parse_form_data(
                    environ=self.env,
                    stream_factory=self._stream_factory,
                    max_form_memory_size=self.options.max_form_memory_size
                )
            except RequestEntityTooLarge:
                raise FalconHeavyRequestEntityTooLarge()

            self._media = form.to_dict(flat=False)
            self._media.update(files.to_dict(flat=False))
            for k, v in iteritems(self._media):
                if len(self._media[k]) == 1:
                    self._media[k] = v[0]

            return self._media

        return super(FalconHeavyRequest, self).media


class FalconHeavyResponse(falcon.Response):

    __slots__ = []

    @property
    def headers(self):
        return self._headers

    def set_header(self, name, value, explode=False):
        if isinstance(value, (tuple, list)):
            value = ','.join(value)
        elif isinstance(value, Mapping):
            if explode:
                value = ','.join('{}={}'.format(k, v) for k, v in iteritems(value))
            else:
                value = ','.join(map(str, chain(*value.items())))

        super(FalconHeavyResponse, self).set_header(name, value)

    def set_headers(self, headers, explode=False):
        if isinstance(headers, dict):
            headers = headers.items()

        for name, value in headers:
            self.set_header(name, value, explode=explode)


class FalconHeavyApi(falcon.API):

    """API providing type casting and validation of requests and responses
    according to the OpenApi specification.

    :param path: Path to specification.
    :param resource_resolver: Falcon resources resolver.
    """

    __slots__ = []

    def __init__(self, path, resource_resolver, **kwargs):
        spec = Object.from_file(OpenApi, path)

        middleware = list(kwargs.pop('middleware', []))
        middleware.append(ValidationMiddleware())

        request_type = kwargs.pop('request_type', None)
        assert request_type is None or issubclass(request_type, FalconHeavyRequest), (
            "Request type MUST be subclass of `FalconHeavyRequest`")

        request_type = request_type or FalconHeavyRequest

        response_type = kwargs.pop('response_type', None)
        assert response_type is None or issubclass(response_type, FalconHeavyResponse), (
            "Response type MUST be subclass of `FalconHeavyResponse`")

        response_type = response_type or FalconHeavyResponse

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
        # the date and date-time objects according to the specification
        self.resp_options.media_handlers = media.Handlers({
            'application/json': FalconHeavyJSONHandler(),
            'application/json; charset=UTF-8': FalconHeavyJSONHandler(),
        })

        for uri_template, path_item in iteritems(spec['paths']):
            resource_id = path_item['x-resource']
            lazy = resource_resolver.resolve(resource_id)

            if lazy is None:
                logger.error(
                    "Resource `%s` is not resolved. Skip path `%s`", resource_id, uri_template)
                continue

            assert callable(lazy), "Resource `{}` MUST be resolved as callable".format(resource_id)

            operation_schemas = {}
            for http_method in falcon.HTTP_METHODS:
                operation = path_item.get(http_method.lower())
                if operation is None:
                    continue

                operation_schema = operation_schemas.setdefault(http_method, {})

                parameters = operation.get('parameters')
                if parameters is not None:
                    operation_schema['parameters'] = ParametersFactory.generate(parameters)

                request_body = operation.get('requestBody')
                if request_body is not None:
                    operation_schema['requestBody'] = RequestBodyFactory.generate(request_body)

                operation_schema['responses'] = ResponsesFactory.generate(operation['responses'])
                operation_schema['security'] = operation.get('security')

            resource = lazy()
            assert resource, "Resource `{}` is not instantiated".format(resource_id)

            setattr(resource, '__operation_schemas', operation_schemas)
            self.add_route(uri_template, resource)
