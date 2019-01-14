from __future__ import unicode_literals, absolute_import

import re
import json
import weakref
import fnmatch
from collections import defaultdict, namedtuple
from functools import cmp_to_key

from six import iteritems
from six.moves import range

from mimeparse import best_match

from werkzeug.datastructures import FileStorage

from ..utils import FormStorage
from ..schema import types
from ..schema.types import Schema
from ..schema.cursor import Cursor
from ..schema.undefined import Undefined
from ..schema.exceptions import SchemaError, UnmarshallingError

from .enums import (
    SCHEMA_TYPES,
    SCHEMA_FORMATS,
    PARAMETER_STYLES,
)


def _generate_integer(schema, type_class=types.IntegerType, required=False):
    return type_class(
        required=required,
        nullable=schema['nullable'],
        default=schema.get('default', Undefined),
        minimum=schema.get('minimum'),
        maximum=schema.get('maximum'),
        exclusive_minimum=schema.get('exclusiveMinimum'),
        exclusive_maximum=schema.get('exclusiveMaximum'),
        multiple_of=schema.get('multipleOf'),
        enum=schema.get('enum')
    )


def generate_integer(schema, required=False):
    return _generate_integer(schema, required=required)


def generate_int32(schema, required=False):
    return _generate_integer(schema, type_class=types.Int32Type, required=required)


def generate_int64(schema, required=False):
    return _generate_integer(schema, type_class=types.Int64Type, required=required)


def generate_float(schema, required=False):
    return types.FloatType(
        required=required,
        nullable=schema['nullable'],
        default=schema.get('default', Undefined),
        minimum=schema.get('minimum'),
        maximum=schema.get('maximum'),
        exclusive_minimum=schema.get('exclusiveMinimum'),
        exclusive_maximum=schema.get('exclusiveMaximum'),
        multiple_of=schema.get('multipleOf'),
        enum=schema.get('enum')
    )


def generate_string(schema, required=False):
    return types.StringType(
        required=required,
        nullable=schema['nullable'],
        default=schema.get('default', Undefined),
        min_length=schema.get('minLength'),
        max_length=schema.get('maxLength'),
        enum=schema.get('enum'),
        pattern=schema.get('pattern')
    )


def generate_boolean(schema, required=False):
    return types.BooleanType(
        required=required,
        nullable=schema['nullable'],
        default=schema.get('default', Undefined),
        enum=schema.get('enum')
    )


def generate_date(schema, required=False):
    return types.DateType(
        required=required,
        nullable=schema['nullable'],
        default=schema.get('default', Undefined),
        enum=schema.get('enum')
    )


def generate_datetime(schema, required=False):
    return types.DateTimeType(
        required=required,
        nullable=schema['nullable'],
        default=schema.get('default', Undefined),
        enum=schema.get('enum')
    )


def generate_uuid(schema, required=False):
    return types.UUIDType(
        required=required,
        nullable=schema['nullable'],
        default=schema.get('default', Undefined),
        enum=schema.get('enum')
    )


def generate_base64(schema, required=False):
    return types.Base64Type(
        nullable=schema['nullable'],
        required=required
    )


def generate_binary(schema, required=False):
    return types.FileType(
        nullable=schema['nullable'],
        required=required
    )


PRIMITIVE_PROPERTY_FACTORIES = {
    (SCHEMA_TYPES.INTEGER, SCHEMA_FORMATS.INT32): generate_int32,
    (SCHEMA_TYPES.INTEGER, SCHEMA_FORMATS.INT64): generate_int64,
    (SCHEMA_TYPES.INTEGER, None): generate_integer,
    (SCHEMA_TYPES.NUMBER, SCHEMA_FORMATS.FLOAT): generate_float,
    (SCHEMA_TYPES.NUMBER, SCHEMA_FORMATS.DOUBLE): generate_float,
    (SCHEMA_TYPES.NUMBER, None): generate_float,
    (SCHEMA_TYPES.STRING, SCHEMA_FORMATS.BYTE): generate_base64,
    (SCHEMA_TYPES.STRING, SCHEMA_FORMATS.BINARY): generate_binary,
    (SCHEMA_TYPES.STRING, SCHEMA_FORMATS.DATE): generate_date,
    (SCHEMA_TYPES.STRING, SCHEMA_FORMATS.DATETIME): generate_datetime,
    (SCHEMA_TYPES.STRING, SCHEMA_FORMATS.PASSWORD): generate_string,
    (SCHEMA_TYPES.STRING, SCHEMA_FORMATS.UUID): generate_uuid,
    (SCHEMA_TYPES.STRING, None): generate_string,
    (SCHEMA_TYPES.BOOLEAN, None): generate_boolean,
}


class PropertyFactory(object):

    @classmethod
    def _generate_discriminator_or_none(cls, schema, subschemas, registry=None):
        """
        Generates discriminator.

        :param schema: Schema object.
        :type schema: Object
        :param subschemas: Explicitly defined subschemas.
        :type subschemas: list of Object
        :param registry: Registry of already generated object types.
        :type registry: dict of ObjectTypes
        :return: Discriminator instance or `None`.
        :rtype: Discriminator | NoneType
        """
        discriminator = schema.get('discriminator')
        if discriminator is None:
            return None

        mapping = {}
        if 'mapping' in discriminator:
            for value, subschema in iteritems(discriminator['mapping']):
                mapping[value] = cls.generate(subschema, registry=registry)

        for subschema in subschemas:
            name = getattr(subschema, 'name', None)
            if name is not None:
                mapping[name] = cls.generate(subschema, registry=registry)

        return types.Discriminator(
            property_name=discriminator['propertyName'],
            mapping=mapping
        )

    @classmethod
    def _generate_object(cls, schema, required=False, registry=None):
        """
        Generates object type.

        :param schema: Schema of object.
        :type schema: Object
        :param required:  Shows whether the property can be undefined.
        :type required: bool
        :param registry: Registry of already generated object types.
        :type registry: dict of ObjectTypes
        :return: Object type.
        :rtype: ObjectType
        """

        # If schema contains `subschemas` attribute, then it meaning
        # that it is super schema and should be generated as `OneOfType`
        if (
                'discriminator' in schema and
                hasattr(schema, 'subschemas') and
                getattr(schema, 'polymorphic', True)
        ):
            # Prevents recursive generation
            setattr(schema, 'polymorphic', False)
            try:
                return types.OneOfType(
                    property_types=[cls.generate(subschema, registry=registry) for subschema in schema.subschemas],
                    discriminator=cls._generate_discriminator_or_none(schema, schema.subschemas, registry=registry),
                    required=required
                )
            finally:
                setattr(schema, 'polymorphic', True)

        key = (schema.url, required)
        registry = registry or {}

        obj = registry.get(key)
        if obj is not None:
            return weakref.proxy(obj)

        obj_schema = Schema(getattr(schema, 'name', schema.url))
        obj = types.ObjectType(
            obj_schema,
            required=required,
            nullable=schema['nullable'],
            default=schema.get('default', Undefined),
            enum=schema.get('enum'),
            min_properties=schema.get('minProperties'),
            max_properties=schema.get('maxProperties')
        )

        registry[key] = obj

        properties = {}
        required = schema.get('required', [])
        for prop_name, prop_schema in iteritems(schema.get('properties', {})):
            properties[prop_name] = cls.generate(
                prop_schema,
                registry=registry,
                required=prop_name in required
            )

        additional_properties = schema.get('additionalProperties')
        if isinstance(additional_properties, types.Object):
            additional_properties = cls.generate(additional_properties, registry=registry)

        obj_schema.properties = properties
        obj_schema.additional_properties = additional_properties

        return obj

    @classmethod
    def _generate_array(cls, schema, required=False, registry=None):
        """
        Generates array type.

        :param schema: Schema of array.
        :type schema: Object
        :param required:  Shows whether the property can be undefined.
        :type required: bool
        :param registry: Registry of already generated object types.
        :type registry: dict of ObjectTypes
        :return: Array type.
        :rtype: ArrayType
        """
        return types.ArrayType(
            item_types=cls.generate(schema['items'], registry=registry),
            required=required,
            nullable=schema['nullable'],
            default=schema.get('default', Undefined),
            unique_items=schema['uniqueItems'],
            min_items=schema.get('minItems'),
            max_items=schema.get('maxItems'),
            enum=schema.get('enum')
        )

    @classmethod
    def generate(cls, schema, required=False, registry=None):
        """
        Generates property by schema.

        :param schema: Schema of property.
        :type schema: Object
        :param required:  Shows whether the property can be undefined.
        :type required: bool
        :param registry: Registry of already generated object types.
        :type registry: dict of ObjectTypes
        :return: Generated property.
        :rtype: AbstractType
        """
        type_ = schema.get('type')
        format_ = schema.get('format')

        if isinstance(type_, list):
            # For ambiguously defined schemas we generate `AnyOfType`
            # with all possible schema interpretations
            inferred = []
            for inferred_type in type_:
                schema['type'] = inferred_type
                inferred.append(cls.generate(schema, registry=registry))

            schema.clear()

            return types.AnyOfType(inferred, required=required)

        elif type_ is not None:
            default_factory = PRIMITIVE_PROPERTY_FACTORIES.get((type_, None))
            property_factory = PRIMITIVE_PROPERTY_FACTORIES.get((type_, format_), default_factory)

            if property_factory:
                return property_factory(schema, required=required)

            if type_ == SCHEMA_TYPES.ARRAY:
                return cls._generate_array(schema, required=required, registry=registry)

            if type_ == SCHEMA_TYPES.OBJECT:
                return cls._generate_object(schema, required=required, registry=registry)

        elif 'allOf' in schema:
            return types.AllOfType(
                property_types=[cls.generate(subschema, registry=registry) for subschema in schema['allOf']],
                required=required
            )

        elif 'anyOf' in schema:
            return types.AnyOfType(
                property_types=[cls.generate(subschema, registry=registry) for subschema in schema['anyOf']],
                discriminator=cls._generate_discriminator_or_none(schema, schema['anyOf'], registry=registry),
                required=required
            )

        elif 'oneOf' in schema:
            return types.OneOfType(
                property_types=[cls.generate(subschema, registry=registry) for subschema in schema['oneOf']],
                discriminator=cls._generate_discriminator_or_none(schema, schema['oneOf'], registry=registry),
                required=required
            )

        elif 'not' in schema:
            return types.NotType(
                property_types=[cls.generate(subschema, registry=registry) for subschema in schema['not']],
                required=required
            )

        else:
            # If type of schema not specified, then generate `AnyType`
            # that accepts any kind of input
            return types.AnyType(
                required=required,
                nullable=schema['nullable'],
                default=schema.get('default', Undefined),
                enum=schema.get('enum')
            )


PARAMETER_VALUE_TYPE = namedtuple(
    'PARAMETER_TYPE',
    ['PRIMITIVE', 'ARRAY', 'OBJECT']
)(
    PRIMITIVE='primitive',
    ARRAY='array',
    OBJECT='object'
)


NotApplicable = Undefined


def parts(l, n):
    """Yield successive n-sized parts from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def style_simple_primitive(value, explode):
    return value


def style_simple_array(value, explode):
    return value.split(',')


def style_simple_objects(value, explode):
    if explode:
        return dict(parts(value.replace('=', ',').split(','), 2))
    else:
        return dict(parts(value.split(','), 2))


def style_label_primitive(value, explode):
    return value[1:]


def style_label_array(value, explode):
    if explode:
        return value[1:].split('.')
    else:
        return value[1:].split(',')


def style_label_object(value, explode):
    if explode:
        return dict(parts(value[1:].replace('=', '.').split('.'), 2))
    else:
        return dict(parts(value[1:].split(','), 2))


def style_matrix_primitive(value, explode):
    return value.rsplit('=', 1)[-1]


def style_matrix_array(value, explode):
    if explode:
        return list(map(lambda x: x.rsplit('=', 1)[1], value[1:].split(';')))
    else:
        return value.rsplit('=', 1)[1].split(',')


def style_matrix_object(value, explode):
    if explode:
        return dict(parts(value[1:].replace('=', ';').split(';'), 2))
    else:
        return dict(parts(value[1:].rsplit('=', 1)[1].split(','), 2))


def style_form_primitive(value, explode):
    return value


def style_form_array(value, explode):
    # Where the parameter appears multiple times in the query string,
    # the value mapped to that parameter key will be a list of all the values in the order seen
    if explode:
        return value
    else:
        return value.split(',')


def style_form_object(value, explode):
    # Couldn't apply form style with explode
    if explode:
        return NotApplicable
    else:
        return dict(parts(value.split(','), 2))


def style_space_delimited_array(value, explode):
    if explode:
        return value
    else:
        return value.split(' ')


def style_pipe_delimited_array(value, explode):
    if explode:
        return value
    else:
        return value.split('|')


def style_not_applicable(*args, **kwargs):
    return NotApplicable


PARAMETER_STYLE_DESERIALIZERS = {
    (PARAMETER_STYLES.SIMPLE, PARAMETER_VALUE_TYPE.PRIMITIVE): style_simple_primitive,
    (PARAMETER_STYLES.SIMPLE, PARAMETER_VALUE_TYPE.ARRAY): style_simple_array,
    (PARAMETER_STYLES.SIMPLE, PARAMETER_VALUE_TYPE.OBJECT): style_simple_objects,
    (PARAMETER_STYLES.LABEL, PARAMETER_VALUE_TYPE.PRIMITIVE): style_label_primitive,
    (PARAMETER_STYLES.LABEL, PARAMETER_VALUE_TYPE.ARRAY): style_label_array,
    (PARAMETER_STYLES.LABEL, PARAMETER_VALUE_TYPE.OBJECT): style_label_object,
    (PARAMETER_STYLES.MATRIX, PARAMETER_VALUE_TYPE.PRIMITIVE): style_matrix_primitive,
    (PARAMETER_STYLES.MATRIX, PARAMETER_VALUE_TYPE.ARRAY): style_matrix_array,
    (PARAMETER_STYLES.MATRIX, PARAMETER_VALUE_TYPE.OBJECT): style_matrix_object,
    (PARAMETER_STYLES.FORM, PARAMETER_VALUE_TYPE.PRIMITIVE): style_form_primitive,
    (PARAMETER_STYLES.FORM, PARAMETER_VALUE_TYPE.ARRAY): style_form_array,
    (PARAMETER_STYLES.FORM, PARAMETER_VALUE_TYPE.OBJECT): style_form_object,
    (PARAMETER_STYLES.SPACE_DELIMITED, PARAMETER_VALUE_TYPE.PRIMITIVE): style_not_applicable,
    (PARAMETER_STYLES.SPACE_DELIMITED, PARAMETER_VALUE_TYPE.ARRAY): style_space_delimited_array,
    (PARAMETER_STYLES.SPACE_DELIMITED, PARAMETER_VALUE_TYPE.OBJECT): style_not_applicable,
    (PARAMETER_STYLES.PIPE_DELIMITED, PARAMETER_VALUE_TYPE.PRIMITIVE): style_not_applicable,
    (PARAMETER_STYLES.PIPE_DELIMITED, PARAMETER_VALUE_TYPE.ARRAY): style_pipe_delimited_array,
    (PARAMETER_STYLES.PIPE_DELIMITED, PARAMETER_VALUE_TYPE.OBJECT): style_not_applicable,
    (PARAMETER_STYLES.DEEP_OBJECT, PARAMETER_VALUE_TYPE.PRIMITIVE): style_not_applicable,
    (PARAMETER_STYLES.DEEP_OBJECT, PARAMETER_VALUE_TYPE.ARRAY): style_not_applicable,
    # Couldn't apply deep object style with explode
    (PARAMETER_STYLES.DEEP_OBJECT, PARAMETER_VALUE_TYPE.OBJECT): style_not_applicable,
}


def get_parameter_value_type(schema):
    """Returns simple parameter value type by schema."""
    type_ = schema.get('type')

    if type_ is None:
        return

    elif type_ == SCHEMA_TYPES.ARRAY:
        return PARAMETER_VALUE_TYPE.ARRAY

    elif type_ == SCHEMA_TYPES.OBJECT:
        return PARAMETER_VALUE_TYPE.OBJECT

    else:
        return PARAMETER_VALUE_TYPE.PRIMITIVE


class ParameterPreprocessor(object):

    """Preprocessor that deserialize request parameters.

    :param value_type: Type of parameter value.
    :type value_type: basestring
    :param style: Serialization method of parameter value.
    :type style: basestring
    :param explode: When this is true, parameter values of type array or object generate
        separate parameters for each value of the array or key-value pair of the map.
        For other types of parameters this property has no effect.
    :type explode: bool
    :param allow_empty: Sets the ability to pass empty-valued parameters.
        Default: True.
    :type allow_empty: bool
    """

    __slots__ = [
        'value_type',
        'style',
        'explode',
        'allow_empty'
    ]

    def __init__(self, value_type, style, explode, allow_empty=True):
        self.value_type = value_type
        self.style = style
        self.explode = explode
        self.allow_empty = allow_empty

    def __call__(self, raw):
        if raw == '' and self.allow_empty is False:
            raise UnmarshallingError("Value can't be empty")

        if raw is Undefined or raw is None:
            return raw

        deserializer = PARAMETER_STYLE_DESERIALIZERS.get((self.style, self.value_type))
        if deserializer is None:
            return raw

        try:
            deserialized = deserializer(raw, self.explode)
        except (TypeError, ValueError, IndexError):
            raise UnmarshallingError("Couldn't apply style")

        if deserialized is NotApplicable:
            return raw

        return deserialized


class ParametersFactory(object):

    @classmethod
    def _generate_parameter(cls, parameter):
        """
        Generates type of parameter.

        :param parameter: Parameter object.
        :type parameter: Object
        :rtype: AbstractType
        """
        schema = parameter.get('schema')
        required = parameter['required']
        if schema is None:
            return types.AnyType(required=required)

        prop = PropertyFactory.generate(schema, required=required)

        parameter_value_type = get_parameter_value_type(schema)
        if parameter_value_type is not None:
            prop.preprocessor = ParameterPreprocessor(
                parameter_value_type,
                parameter['style'],
                parameter['explode'],
                allow_empty=parameter.get('allowEmptyValue')
            )

        return prop

    @classmethod
    def _generate_location(cls, location, parameters):
        """
        Generates type of parameters with specific location.

        :param location: Location of parameters.
        :type location: basestring
        :param parameters: Parameters with specified location.
        :type parameters: list of Object
        :rtype: ObjectType
        """
        return types.ObjectType(Schema(
            name=location.capitalize(),
            properties={parameter['name']: cls._generate_parameter(parameter) for parameter in parameters}
        ))

    @classmethod
    def generate(cls, parameters):
        """
        Generates type of request parameters.

        :param parameters: Defined parameters.
        :type parameters: list of Object
        :rtype: ObjectType
        """
        locations = defaultdict(list)
        if parameters:
            for parameter in parameters:
                locations[parameter['in']].append(parameter)

        return types.ObjectType(
            Schema(
                name='Parameters',
                pattern_properties=[
                    (
                        re.compile(r'^{}$'.format(location.lower()), re.IGNORECASE),
                        cls._generate_location(location, params)
                    )
                    for location, params in iteritems(locations)
                ]
            ),
            strict=False
        )


class HeadersFactory(object):

    @classmethod
    def generate(cls, headers):
        """
        Generates type of request headers.

        :param headers: Dictionary of header objects.
        :type headers: dict of Object
        :rtype: ObjectType
        """
        properties = {}
        for name, header in iteritems(headers):
            # Headers names are case insensitive
            name = name.lower()

            schema = header.get('schema')
            required = header['required']

            if name == 'content-type':
                continue

            elif schema is None:
                properties[name] = types.AnyType(required=required)
                continue

            prop = PropertyFactory.generate(schema, required=required)

            parameter_value_type = get_parameter_value_type(schema)

            if parameter_value_type is not None:
                prop.preprocessor = ParameterPreprocessor(
                    parameter_value_type,
                    header['style'],
                    header['explode']
                )

            properties[name] = prop

        return types.ObjectType(
            Schema(
                'Headers',
                properties=properties
            ),
            strict=False
        )


def _cmp(left, right):
    """Python 3 compatible comparator."""
    return (left > right) - (left < right)


class MultipartPreprocessor(object):

    """Preprocessor of parts of multipart content.

    :param allowed_content_types: Allowed content types for current part.
    :type allowed_content_types: list of basestring
    :param headers: Type of headers.
    :type headers: `ObjectType`
    """

    __slots__ = [
        'allowed_content_types',
        'headers'
    ]

    def __init__(self, allowed_content_types, headers):
        self.allowed_content_types = allowed_content_types
        self.headers = headers

    def _process(self, value):
        if isinstance(value, FormStorage):
            content_type = value.content_type or 'text/plain'

        elif isinstance(value, FileStorage):
            content_type = value.content_type or 'application/octet-stream'

        else:
            return value

        if self.allowed_content_types:
            if not best_match(self.allowed_content_types, content_type):
                raise UnmarshallingError(
                    "Unsupported content type. Allowed one of: {}".format(', '.join(self.allowed_content_types)))

        if self.headers:
            try:
                headers = {k.lower(): v for k, v in iteritems(value.headers)}
            except AttributeError:
                headers = None

            if headers is not None:
                try:
                    value.cleaned_headers = self.headers.unmarshal(Cursor.from_raw(raw=headers))
                except SchemaError as e:
                    raise UnmarshallingError({'headers': e.errors})

        if not isinstance(value, FormStorage):
            return value

        if 'application/json' in content_type:
            try:
                return json.loads(value)
            except ValueError:
                raise UnmarshallingError("Invalid JSON data")

        return value

    def __call__(self, value):
        if value is Undefined or value is None:
            return value

        # Parts with the same names combines into a list
        if isinstance(value, list):
            return [self._process(item) for item in value]

        else:
            return self._process(value)


def _get_default_content_type(schema):
    type_ = schema.get('type')
    format_ = schema.get('format')

    if type_ in (SCHEMA_TYPES.ARRAY, SCHEMA_TYPES.OBJECT):
        return 'application/json'

    elif type_ == SCHEMA_TYPES.STRING and format_ in (SCHEMA_FORMATS.BINARY, SCHEMA_FORMATS.BYTE):
        return 'application/octet-stream'

    elif type_ is not None:
        return 'text/plain'

    else:
        return


def get_default_content_type(schema):
    """Returns default content type for part of multipart content by schema."""
    type_ = schema.get('type')

    if type_ == SCHEMA_TYPES.ARRAY:
        return _get_default_content_type(schema['items'])

    else:
        return _get_default_content_type(schema)


class ContentFactory(object):

    @classmethod
    def _generate_media(cls, media_type, content_type):
        """
        Generates media type.

        :param media_type: Media type object.
        :type media_type: Object
        :param content_type: Content type of this media type.
        :type content_type: basestring
        :rtype: AbstractType
        """
        schema = media_type.get('schema')
        if schema is not None:
            media = PropertyFactory.generate(schema)

            is_multipart = 'multipart/form-data' in content_type
            is_urlencoded = any(ct in content_type for ct in (
                'application/x-www-form-urlencoded',
                'application/x-url-encoded',
            ))

            if is_multipart or is_urlencoded:
                media.strict = False

            encoding = media_type.get('encoding')
            properties = schema.get('properties')

            # The encoding object SHALL only apply to requestBody objects
            # when the media type is multipart or application/x-www-form-urlencoded
            if (
                    (is_multipart or is_urlencoded) and
                    isinstance(media, types.ObjectType) and
                    encoding is not None and
                    properties is not None
            ):
                for prop_name, prop in iteritems(media.schema.properties):
                    prop_encoding = encoding.get(prop_name)
                    prop_schema = properties.get(prop_name)

                    if prop_schema is None:
                        continue

                    if is_multipart:
                        prop_content_type = prop_encoding is not None and prop_encoding.get('contentType')
                        prop_headers = prop_encoding is not None and prop_encoding.get('headers')

                        allowed_content_types = None
                        if prop_content_type:
                            allowed_content_types = map(lambda x: x.strip(), prop_content_type.split(','))

                        else:
                            default_content_type = get_default_content_type(prop_schema)
                            if default_content_type is not None:
                                allowed_content_types = [default_content_type]

                        headers = None
                        if prop_headers:
                            headers = HeadersFactory.generate(prop_headers)

                        prop.preprocessor = MultipartPreprocessor(allowed_content_types, headers)

                    else:
                        style = PARAMETER_STYLES.FORM
                        explode = True
                        if prop_encoding is not None:
                            style = prop_encoding['style']
                            explode = prop_encoding['explode']

                        prop.preprocessor = ParameterPreprocessor(
                            get_parameter_value_type(prop_schema), style, explode)

        else:
            media = types.AnyType()

        return media

    @classmethod
    def generate(cls, content):
        """
        Generates pattern properties items of request contents.

        :param content: Mapping of content types with corresponding media type objects.
        :type content: dict of Object
        :rtype: list of tuple
        """
        content_types = []
        for content_type, media_type in iteritems(content):
            # Content types without params we makes more general
            if not content_type.endswith('*') and ';' not in content_type:
                content_types.append((content_type + '*', media_type))

            else:
                content_types.append((content_type, media_type))

        # The most specific key is applicable. e.g. text/plain overrides text/*
        content_types.sort(key=cmp_to_key(lambda x, y: _cmp(x[0].count('*'), y[0].count('*'))))

        result = []
        for content_type, media_type in content_types:
            result.append((
                re.compile(fnmatch.translate(content_type), re.IGNORECASE),
                cls._generate_media(media_type, content_type)
            ))

        return result


class RequestBodyFactory(object):

    @classmethod
    def generate(cls, request_body):
        """
        Generates type of request body.

        :param request_body: Request body object.
        :type request_body: Object
        :rtype: ObjectType
        """
        return types.ObjectType(
            Schema(
                name='RequestBody',
                pattern_properties=ContentFactory.generate(request_body['content']),
                additional_properties=False,
            ),
            required=request_body['required'],
            messages={
                'required': "Request body is required",
                'additional_properties': "Unexpected content-type `{0}`"
            }
        )


def response_codes_comparator(left, right):
    """More common codes shifts to tail."""
    if left == 'default':
        return 1

    if right == 'default':
        return -1

    return _cmp(left.count('X'), right.count('X'))


class ResponsesFactory(object):

    @classmethod
    def _generate_content(cls, content):
        """
        Generates type of response content.

        :param content: Mapping of content types with corresponding media type objects.
        :type content: dict of Object
        :rtype:  AnyType | ObjectType
        """
        if content is not None:
            return types.ObjectType(
                Schema(
                    name='Content',
                    pattern_properties=ContentFactory.generate(content),
                    additional_properties=False
                ),
                messages={
                    'additional_properties': "Unexpected content-type `{0}`"
                }
            )

        else:
            return types.AnyType()

    @classmethod
    def _generate_headers(cls, headers):
        """
        Generates type of response headers.

        :param headers: Dictionary of header objects.
        :type headers: dict of Object | NoneType
        :rtype: AnyType | ObjectType
        """
        if headers is not None:
            return HeadersFactory.generate(headers)
        else:
            return types.AnyType()

    @classmethod
    def _code_translate(cls, code):
        """
        Translates code into regular expression.

        :param code: Code of response.
        :rtype: basestring
        """
        if code == 'default':
            return r'^\d{3}$'
        else:
            return r'^{}$'.format(code.replace('X', r'\d{1}'))

    @classmethod
    def _generate_response(cls, code, response):
        """
        Generates item of pattern properties for specified response.

        :param code: Response code.
        :type code: basestring
        :param response: Response object.
        :type response: Object
        :rtype: Object
        """
        return (
            re.compile(cls._code_translate(code)),
            types.ObjectType(
                Schema(
                    name='Response',
                    properties={
                        'content': cls._generate_content(response.get('content')),
                        'headers': cls._generate_headers(response.get('headers')),
                    },
                    additional_properties=False
                )
            )
        )

    @classmethod
    def generate(cls, responses):
        """
        Generates type of responses.

        :param responses: Mapping of response codes with corresponding response objects.
        :type responses: dict of Object
        :rtype: ObjectType
        """
        codes = sorted(responses, key=cmp_to_key(response_codes_comparator))

        return types.ObjectType(
            Schema(
                name='Responses',
                pattern_properties=[cls._generate_response(code, responses[code]) for code in codes],
                additional_properties=False,
            ),
            messages={
                'additional_properties': "Unexpected response code `{0}`"
            }
        )
