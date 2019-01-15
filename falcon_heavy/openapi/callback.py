from __future__ import unicode_literals

from ..schema import types

from .base import BaseOpenApiObjectType


class CallbackObjectType(BaseOpenApiObjectType):

    __slots__ = []

    ADDITIONAL_PROPERTIES = types.LazyType(lambda: PathItemObjectType())


from .path_item import PathItemObjectType  # noqa
