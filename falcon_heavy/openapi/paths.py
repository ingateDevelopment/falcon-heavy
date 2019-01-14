import re

from ..schema import types

from .path_item import PathItem, update_parameters


Paths = types.Schema(
    name='Paths',
    pattern_properties=[
        (re.compile(r'^x-'), types.AnyType()),
        (re.compile(r'^/'), types.ObjectOrReferenceType(PathItem, postprocessor=update_parameters))
    ],
    additional_properties=False
)
