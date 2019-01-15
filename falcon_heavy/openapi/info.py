from __future__ import unicode_literals

from ..schema import types

from .base import BaseOpenApiObjectType
from .contact import ContactObjectType
from .license import LicenseObjectType


class InfoObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'title': types.StringType(),
        'description': types.StringType(),
        'termsOfService': types.UriType(),
        'contact': ContactObjectType(),
        'license': LicenseObjectType(),
        'version': types.StringType()
    }

    REQUIRED = {
        'title',
        'version'
    }
