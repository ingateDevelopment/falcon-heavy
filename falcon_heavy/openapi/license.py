from ..schema import types


License = types.Schema(
    name='License',
    additional_properties=False,
    properties={
        'name': types.StringType(required=True),
        'url': types.UrlType()
    }
)
