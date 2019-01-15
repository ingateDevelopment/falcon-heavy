from __future__ import unicode_literals

from .._compat import ChainMap

from ..schema import types

from .base import BaseOpenApiObjectType
from .types import ReferencedType
from .operation import OperationObjectType
from .server import ServerObjectType
from .parameter import ParameterPolymorphic
from .enums import HTTP_METHODS


class PathItemObjectType(BaseOpenApiObjectType):

    __slots__ = []

    PROPERTIES = {
        'summary': types.StringType(),
        'description': types.StringType(),

        'get': OperationObjectType(),
        'put': OperationObjectType(),
        'post': OperationObjectType(),
        'delete': OperationObjectType(),
        'options': OperationObjectType(),
        'head': OperationObjectType(),
        'patch': OperationObjectType(),
        'trace': OperationObjectType(),

        'servers': types.ArrayType(ServerObjectType()),
        'parameters': types.ArrayType(
            ReferencedType(ParameterPolymorphic),
            unique_items=True,
            unique_item_properties=['in', 'name']
        ),

        # This field used for internal association to falcon resource
        'x-resource': types.StringType()
    }

    REQUIRED = {
        'x-resource'
    }

    @staticmethod
    def _parameters_dict(parameters):
        """Returns dictionary with parameters mapped to key that contains
        location of parameter and it name

        :param parameters: list of parameters
        :type parameters: list of Object
        :return: dictionary of parameters
        :rtype: dict of Object
        """
        return {(parameter['in'], parameter['name']): parameter for parameter in parameters}

    def _convert(self, raw, path, **context):
        converted = super(PathItemObjectType, self)._convert(raw, path, **context)

        # Update parameters of each operation by common parameters
        common_parameters = converted.get('parameters')
        if common_parameters is not None:
            common_parameters = self._parameters_dict(common_parameters)

            for http_method in HTTP_METHODS:
                operation = converted.get(http_method)
                if operation is None:
                    continue

                parameters = operation.get('parameters')
                if parameters is None:
                    operation.properties['parameters'] = common_parameters.values()

                else:
                    operation['parameters'] = ChainMap(
                        self._parameters_dict(parameters), common_parameters).values()

        return converted
