from ..schema import types

from .parameter import HeaderParameter


Header = types.Schema(
    name='Header',
    bases=HeaderParameter,
    properties={
        'name': types.StringType(),
        'in': types.StringType(default='header', enum=['header'])
    }
)
