from __future__ import unicode_literals

from ..schema import types

from .base import BaseOpenApiObjectType
from .oauth_flows import OAuthFlowsObjectType
from .enums import SECURITY_SCHEME_TYPES, PARAMETER_LOCATIONS


class BaseSecuritySchemeObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'type': types.StringType(enum=SECURITY_SCHEME_TYPES),
        'description': types.StringType()
    }

    REQUIRED = {
        'type'
    }


class ApiKeySecuritySchemeObjectType(BaseSecuritySchemeObjectType):

    __slots__ = []

    PROPERTIES = {
        'name': types.StringType(),
        'in': types.StringType(
            enum=(PARAMETER_LOCATIONS.QUERY, PARAMETER_LOCATIONS.HEADER, PARAMETER_LOCATIONS.COOKIE)
        )
    }

    REQUIRED = {
        'name',
        'in'
    }


class HttpSecuritySchemeObjectType(BaseSecuritySchemeObjectType):

    __slots__ = []

    PROPERTIES = {
        'scheme': types.StringType(),
        'bearerFormat': types.StringType()
    }

    REQUIRED = {
        'scheme'
    }


class OAuth2SecuritySchemeObjectType(BaseSecuritySchemeObjectType):

    __slots__ = []

    PROPERTIES = {
        'flows': OAuthFlowsObjectType()
    }

    REQUIRED = {
        'flows'
    }


class OpenIdConnectSecuritySchemeObjectType(BaseSecuritySchemeObjectType):

    __slots__ = []

    PROPERTIES = {
        'openIdConnectUrl': types.StringType()
    }

    REQUIRED = {
        'openIdConnectUrl'
    }


SecuritySchemePolymorphic = types.DiscriminatorType(
    property_name='type',
    mapping={
        'apiKey': ApiKeySecuritySchemeObjectType(),
        'http': HttpSecuritySchemeObjectType(),
        'oauth2': OAuth2SecuritySchemeObjectType(),
        'openIdConnect': OpenIdConnectSecuritySchemeObjectType()
    }
)
