from __future__ import unicode_literals

from ..schema import types


class SecurityRequirementObjectType(types.ObjectType):

    __slots__ = []

    ADDITIONAL_PROPERTIES = types.ArrayType(types.StringType())
