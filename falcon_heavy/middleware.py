from __future__ import absolute_import

from falcon import errors as http_errors

from .schema.exceptions import SchemaError
from .schema.cursor import Cursor
from .schema.undefined import Undefined
from .openapi.enums import PARAMETER_LOCATIONS
from .utils import coalesce
from .errors import FalconHeavyInvalidRequest
from . import logger


def operation_schema(f):
    """Provide operation schema as not `None` positional argument."""

    def wrapper(self, req, resp, resource, *args, **kwargs):
        if resource is None:
            return

        operation_schemas = getattr(resource, '__operation_schemas', None)

        schema = None
        if operation_schemas is not None:
            schema = operation_schemas.get(req.method)

        if schema is None:
            return

        return f(self, req, resp, resource, schema, *args, **kwargs)

    return wrapper


class ValidationMiddleware(object):

    @operation_schema
    def process_resource(self, req, resp, resource, schema, params):
        parameters = {
            PARAMETER_LOCATIONS.PATH: params,
            PARAMETER_LOCATIONS.QUERY: req.params,
            PARAMETER_LOCATIONS.HEADER: req.headers,
            PARAMETER_LOCATIONS.COOKIE: req.cookies
        }

        # Request body is presented if content length more than zero
        try:
            body = req.media if req.content_length else None
        except http_errors.HTTPUnsupportedMediaType:
            body = req.bounded_stream

        errors = {}

        unmarshalled_parameters = parameters
        if 'parameters' in schema:
            try:
                unmarshalled_parameters = schema['parameters'].unmarshal(
                    Cursor.from_raw(raw=parameters))
            except SchemaError as e:
                errors.update(e.errors)

        unmarshalled_body = body
        if 'requestBody' in schema:
            try:
                unmarshalled_body = schema['requestBody'].unmarshal(Cursor.from_raw(
                    raw={req.content_type: body} if body is not None else Undefined
                ))
            except SchemaError as e:
                if isinstance(e.errors, dict) and req.content_type in e.errors:
                    errors.update({'body': e.errors[req.content_type]})
                else:
                    errors.update({'body': e.errors})

            unmarshalled_body = unmarshalled_body.get(req.content_type)

        if errors:
            logger.error("Invalid request `%s`: %s", req.path, errors)
            raise FalconHeavyInvalidRequest(data=errors)

        for location in PARAMETER_LOCATIONS:
            setattr(req, '{}_params'.format(location), unmarshalled_parameters[location])

        req.body = unmarshalled_body

    @operation_schema
    def process_response(self, req, resp, resource, schema):
        content = coalesce(resp.media, resp.body, resp.data, resp.stream_len and resp.stream)

        try:
            schema['responses'].unmarshal(Cursor.from_raw(raw={
                resp.status[:3]: {
                    'content': {resp.content_type: content} if resp.content_type else {},
                    'headers': resp.headers
                }
            }))
        except SchemaError as e:
            logger.error("Invalid response `%s`: %s", req.path, e)


class AbstractAuthMiddleware(object):

    def process_security_requirement(self, security_requirement, req, resp, resource, params):
        raise NotImplementedError

    @operation_schema
    def process_resource(self, req, resp, resource, schema, params):
        security_requirements = schema.get('security')
        if security_requirements is not None:
            for security_requirement in security_requirements:
                self.process_security_requirement(security_requirement, req, resp, resource, params)
