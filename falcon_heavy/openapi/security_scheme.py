from ..schema import types

from .oauth_flows import OAuthFlows
from .extensions import SpecificationExtensions


BaseSecurityScheme = types.Schema(
    name='BaseSecurityScheme',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'type': types.StringType(required=True, enum=("apiKey", "http", "oauth2", "openIdConnect")),
        'description': types.StringType()
    }
)


ApiKeySecurityScheme = types.Schema(
    name='ApiKeySecurityScheme',
    bases=BaseSecurityScheme,
    properties={
        'name': types.StringType(required=True),
        'in': types.StringType(required=True, enum=("query", "header", "cookie"))
    }
)


HttpSecurityScheme = types.Schema(
    name='HttpSecurityScheme',
    bases=BaseSecurityScheme,
    properties={
        'scheme': types.StringType(required=True),
        'bearerFormat': types.StringType()
    }
)


OAuth2SecurityScheme = types.Schema(
    name='OAuth2SecurityScheme',
    bases=BaseSecurityScheme,
    properties={
        'flows': types.ObjectType(OAuthFlows, required=True)
    }
)


OpenIdConnectSecurityScheme = types.Schema(
    name='OpenIdConnectSecurityScheme',
    bases=BaseSecurityScheme,
    properties={
        'openIdConnectUrl': types.StringType(required=True)
    }
)


SecurityScheme = types.OneOfType(
    property_types=[],
    discriminator=types.Discriminator(
        property_name='type',
        mapping={
            'apiKey': types.ObjectOrReferenceType(ApiKeySecurityScheme),
            'http': types.ObjectOrReferenceType(HttpSecurityScheme),
            'oauth2': types.ObjectOrReferenceType(OAuth2SecurityScheme),
            'openIdConnect': types.ObjectOrReferenceType(OpenIdConnectSecurityScheme)
        }
    )
)
