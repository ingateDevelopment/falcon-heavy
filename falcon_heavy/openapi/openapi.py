import re

from ..schema import types

from .external_documentation import ExternalDocumentation
from .paths import Paths
from .info import Info
from .tag import Tag
from .server import Server
from .components import Components
from .extensions import SpecificationExtensions


OPENAPI_VERSION = '3.0.1'


OpenApi = types.Schema(
    name='OpenApi',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'openapi': types.StringType(required=True, pattern=re.compile(r'^3\.\d+\.\d+$')),
        'info': types.ObjectType(Info, required=True),
        'servers': types.ArrayType(types.ObjectType(Server)),
        'paths': types.ObjectType(
            Paths,
            required=True,
            messages={'additional_properties': "Path MUST be starts with slash"}
        ),
        'components': types.ObjectType(Components),
        'security': types.DictType(types.ArrayType(types.StringType())),
        'tags': types.ArrayType(types.ObjectType(Tag), unique_items=True, key='name'),
        'externalDocs': types.ObjectType(ExternalDocumentation)
    }
)
