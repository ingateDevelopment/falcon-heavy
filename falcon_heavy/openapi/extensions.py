import re

from ..schema import types


SpecificationExtensions = [
    (re.compile(r'^x-'), types.AnyType())
]
