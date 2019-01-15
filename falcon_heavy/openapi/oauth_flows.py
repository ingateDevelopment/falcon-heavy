from __future__ import unicode_literals

from .base import BaseOpenApiObjectType
from .oauth_flow import OAuthFlowObjectType


class OAuthFlowsObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'implicit': OAuthFlowObjectType(),
        'password': OAuthFlowObjectType(),
        'clientCredentials': OAuthFlowObjectType(),
        'authorizationCode': OAuthFlowObjectType()
    }
