from ..schema import types

from .enums import PARAMETER_STYLES
from .extensions import SpecificationExtensions


Encoding = types.Schema(
    name='Encoding',
    pattern_properties=SpecificationExtensions,
    additional_properties=False,
    properties={
        'contentType': types.StringType(),
        'headers': types.DictType(types.ObjectOrReferenceType(lambda: Header)),
        'style': types.StringType(default=PARAMETER_STYLES.FORM, enum=PARAMETER_STYLES),
        'explode': types.BooleanType(),
        'allowReserved': types.BooleanType(default=False)
    },
    defaults={
        'explode': lambda data, value: value['style'] == PARAMETER_STYLES.FORM
    }
)


from .header import Header  # noqa
