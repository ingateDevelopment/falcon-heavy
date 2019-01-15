from __future__ import unicode_literals

from ..schema import types

from .parameter import BaseParameterObjectType
from .enums import PARAMETER_STYLES


class HeaderObjectType(BaseParameterObjectType):

    __slots__ = []

    MESSAGES = {
        'deprecated': "Header '{0}' is deprecated"
    }

    PROPERTIES = {
        'style': types.StringType(enum=(PARAMETER_STYLES.SIMPLE, ), default=PARAMETER_STYLES.SIMPLE),
        'explode': types.BooleanType(default=False)
    }
