from ..schema import types

from .extensions import SpecificationExtensions


OAuthFlow = types.Schema(
    name='OAuthFlow',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'authorizationUrl': types.StringType(required=True),
        'tokenUrl': types.StringType(required=True),
        'refreshUrl': types.StringType(),
        'scopes': types.DictType(types.StringType(), required=True)
    }
)


OAuthFlows = types.Schema(
    name='OAuthFlows',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'implicit': types.ObjectType(OAuthFlow),
        'password': types.ObjectType(OAuthFlow),
        'clientCredentials': types.ObjectType(OAuthFlow),
        'authorizationCode': types.ObjectType(OAuthFlow)
    }
)
