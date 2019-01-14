from ..schema import types

from .extensions import SpecificationExtensions


Callback = types.Schema(
    name='Callback',
    pattern_properties=SpecificationExtensions,
    additional_properties=types.ObjectType(lambda: PathItem)
)


from .path_item import PathItem  # noqa
