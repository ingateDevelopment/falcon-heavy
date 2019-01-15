from __future__ import absolute_import

from falcon import errors as http_errors

from .schema.exceptions import SchemaError
from .schema.path import Path
from .schema.undefined import Undefined
from .openapi.enums import PARAMETER_LOCATIONS
from .utils.functional import coalesce
from . import logger


def operation_schema(responder):
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

        return responder(self, req, resp, resource, schema, *args, **kwargs)

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
            content = req.media if req.content_length else None
        except http_errors.HTTPUnsupportedMediaType:
            content = req.bounded_stream

        if 'request' in schema:
            try:
                converted_request = schema['request'].convert(
                    {
                        'parameters': parameters,
                        'body': {
                            'content': {req.content_type: content} if content is not None else Undefined
                        }
                    },
                    Path('#/request'),
                    strict=True
                )

                converted_parameters = converted_request['parameters']
                converted_content = converted_request['body'].get('content', content)

                for location in PARAMETER_LOCATIONS:
                    setattr(req, '{}_params'.format(location), converted_parameters[location])

                req.content = converted_content

            except SchemaError as e:
                print("Invalid request at %s\n\n%s" % (req.uri_template, e))
                logger.error("Invalid request at %s:\n\n%s", req.uri_template, e)
                raise http_errors.HTTPBadRequest(description=str(e))

    @operation_schema
    def process_response(self, req, resp, resource, schema):
        content = coalesce(resp.body, resp.media, resp.stream_len and resp.stream)

        try:
            converted_response = schema['responses'].convert(
                {
                    resp.status[:3]: {
                        'content': {resp.content_type: content} if resp.content_type else {},
                        'headers': resp.headers
                    }
                },
                Path('#/response'),
                strict=True
            )


        except SchemaError as e:
            print("Invalid response at %s\n\n%s" % (req.uri_template, e))
            logger.error("Invalid response at %s\n\n%s", req.uri_template, e)


class AbstractAuthMiddleware(object):

    def process_security_requirement(self, security_requirement, req, resp, resource, params):
        raise NotImplementedError

    @operation_schema
    def process_resource(self, req, resp, resource, schema, params):
        security_requirements = schema.get('security')
        if security_requirements is not None:
            for security_requirement in security_requirements:
                self.process_security_requirement(security_requirement, req, resp, resource, params)
