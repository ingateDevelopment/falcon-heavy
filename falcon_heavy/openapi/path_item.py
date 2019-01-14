from ..schema import types, compat

from .operation import Operation
from .server import Server
from .parameter import Parameter
from .extensions import SpecificationExtensions
from .enums import HTTP_METHODS


def parameters_dict(parameters):
    """
    Returns dictionary with parameters mapped to key that contains location of parameter and it name.

    :param parameters: List of parameters.
    :type parameters: list of Object
    :return: Dictionary of parameters.
    :rtype: dict of Object
    """
    return {(parameter['in'], parameter['name']): parameter for parameter in parameters}


def update_parameters(value):
    """
    Update parameters of each operation by common parameters defined on `PathItem` level.

    :param value: PathItem object.
    :type value: Object
    :return: PathItem object with updated operations
    :rtype: Object
    """
    common_parameters = value.get('parameters')
    if common_parameters is None:
        return value

    common_parameters = parameters_dict(common_parameters)

    for http_method in HTTP_METHODS:
        operation = value.get(http_method)
        if operation is None:
            continue

        parameters = operation.get('parameters')
        if parameters is None:
            operation.properties['parameters'] = common_parameters.values()

        else:
            operation['parameters'] = compat.ChainMap(
                parameters_dict(parameters), common_parameters).values()

    del value['parameters']

    return value


PathItem = types.Schema(
    name='PathItem',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'summary': types.StringType(),
        'description': types.StringType(),

        'get': types.ObjectType(Operation),
        'put': types.ObjectType(Operation),
        'post': types.ObjectType(Operation),
        'delete': types.ObjectType(Operation),
        'options': types.ObjectType(Operation),
        'head': types.ObjectType(Operation),
        'patch': types.ObjectType(Operation),
        'trace': types.ObjectType(Operation),

        'servers': types.ArrayType(types.ObjectType(Server)),
        'parameters': types.ArrayType(
            Parameter,
            unique_items=True,
            key=lambda parameter: (parameter['name'], parameter['in'])
        ),

        # It's field required for internal association to falcon resource
        'x-resource': types.StringType(required=True)
    }
)
