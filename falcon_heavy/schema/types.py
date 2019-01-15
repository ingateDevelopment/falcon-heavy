from __future__ import unicode_literals

import re
import json
import datetime
import operator
import decimal
from collections import OrderedDict
from distutils.util import strtobool

import rfc3987
from strict_rfc3339 import InvalidRFC3339Error, rfc3339_to_timestamp

from six import string_types, integer_types, iteritems, iterkeys, with_metaclass
from six.moves import StringIO, reduce

from ..utils.encoding import (
    Base64EncodableStream,
    Base64DecodableStream
)

from ..utils.functional import cached_property
from ..utils.encoding import force_text

from .._compat import ChainMap, Mapping

from .undefined import Undefined
from .utils import uniq, is_flo
from .exceptions import (
    Error,
    SchemaError
)


class Object(ChainMap):

    """Object

    Contains property values
    """

    def __init__(self,
                 properties=None,
                 pattern_properties=None,
                 additional_properties=None):
        super(Object, self).__init__(
            properties or {},
            pattern_properties or {},
            additional_properties or {}
        )

    @property
    def properties(self):
        return self.maps[0]

    @property
    def pattern_properties(self):
        return self.maps[1]

    @property
    def additional_properties(self):
        return self.maps[2]

    def __delitem__(self, key):
        did_delete = False
        for data in self.maps:
            try:
                del data[key]
                did_delete = True
            except KeyError:
                pass
        if not did_delete:
            raise KeyError(key)

    def __repr__(self):
        return "%s(%r, %r, %r)" % (
            self.__class__.__name__,
            self.properties,
            self.pattern_properties,
            self.additional_properties
        )

    def __or__(self, other):
        if not isinstance(other, Mapping):
            raise NotImplemented

        if isinstance(other, Object):
            assert len(self.maps) == len(other.maps)
            for l, r in zip(self.maps, other.maps):
                l.update(r)
        else:
            self.additional_properties.update(other)

        return self

    def __hash__(self):
        return hash(json.dumps(self, sort_keys=True))


class ConvertibleMeta(type):

    def __new__(mcs, name, bases, attrs):
        messages = {}

        for base in reversed(bases):
            if hasattr(base, 'MESSAGES'):
                messages.update(base.MESSAGES)

        if 'MESSAGES' in attrs:
            messages.update(attrs['MESSAGES'])

        klass = type.__new__(mcs, name, bases, attrs)
        klass.MESSAGES = messages

        return klass


class AbstractConvertible(with_metaclass(ConvertibleMeta, object)):

    __slots__ = [
        '__weakref__',
        'messages'
    ]

    def __init__(self, messages=None):
        self.messages = dict(self.MESSAGES, **(messages or {}))

    def convert(self, raw, path, **context):
        """Returns converted and valid value"""
        raise NotImplementedError


class TypeMeta(ConvertibleMeta):

    def __new__(mcs, name, bases, attrs):
        validators = OrderedDict()

        for base in reversed(bases):
            if hasattr(base, "VALIDATORS"):
                validators.update(base.VALIDATORS)

        for attr_name, attr in attrs.items():
            if attr_name.startswith('validate_'):
                validators[attr_name] = 1

        klass = ConvertibleMeta.__new__(mcs, name, bases, attrs)
        klass.VALIDATORS = validators

        return klass


class AbstractType(with_metaclass(TypeMeta, AbstractConvertible)):

    """Abstract type

    :param default: default value
    :type default: any
    :param nullable: invalidate the property when value is None
    :type nullable: bool
    :param enum: determines the possible values of the property
    :type enum: list of any
    """

    MESSAGES = {
        'nullable': "Null values not allowed",
        'enum': "Should be equal to one of the allowed values. Allowed values: {0}"
    }

    __slots__ = [
        'default',
        'nullable',
        'enum',
        'validators'
    ]

    def __init__(self, default=Undefined, nullable=False, enum=None, validators=None, **kwargs):
        self.default = default
        self.nullable = nullable
        self.enum = enum

        self.validators = [getattr(self, validator_name) for validator_name in self.VALIDATORS]
        if validators:
            self.validators.extend(validators)

        super(AbstractType, self).__init__(**kwargs)

    def _convert(self, raw, path, **context):
        raise NotImplementedError

    def convert(self, raw, path, **context):
        if not self.nullable and raw is None:
            raise SchemaError(Error(path, self.messages['nullable']))

        if raw is None:
            return None

        if raw is Undefined:
            if self.default is Undefined:
                return Undefined
            else:
                raw = self.default
                converted = self._convert(raw, path, **context)
        else:
            converted = self._convert(raw, path, **context)

        errors = []
        for validator in self.validators:
            message = validator(converted, raw)
            if message is not None:
                errors.append(Error(path, message))

        if errors:
            raise SchemaError(*errors)

        return converted

    def validate_enum(self, converted, raw):
        if self.enum and raw not in self.enum and converted not in self.enum:
            return self.messages['enum'].format(', '.join(sorted(map(str, self.enum))))


class AnyType(AbstractType):

    """Any type"""

    __slots__ = []

    def _convert(self, raw, path, **context):
        return raw


class StringType(AbstractType):

    """String type

    :param min_length: invalidate the property when value length less than specified
    :type min_length: int
    :param max_length: invalidate the property when value length greater than specified
    :type max_length: int
    :param pattern: invalidate when value is not match to specified pattern
    :type pattern: re._pattern_type
    """

    MESSAGES = {
        'type': "Should be a string",
        'min_length': "Must be no less than {0} characters in length",
        'max_length': "Must be no greater than {0} characters in length",
        'pattern': "Does not match to pattern"
    }

    __slots__ = [
        'min_length',
        'max_length',
        'pattern'
    ]

    def __init__(self, min_length=None, max_length=None, pattern=None, **kwargs):
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        super(StringType, self).__init__(**kwargs)

    def _convert(self, raw, path, strict=True, **context):
        if isinstance(raw, string_types):
            return raw

        if strict:
            raise SchemaError(Error(path, self.messages['type']))

        return force_text(raw, errors='replace')

    def validate_length(self, converted, raw):
        if self.min_length is not None and len(converted) < self.min_length:
            return self.messages['min_length'].format(self.min_length)

        if self.max_length is not None and len(converted) > self.max_length:
            return self.messages['max_length'].format(self.max_length)

    def validate_pattern(self, converted, raw):
        if self.pattern is not None and self.pattern.match(converted) is None:
            return self.messages['pattern']


class NumberType(AbstractType):

    """Number type

    :param minimum: invalidate the property when value less than specified minimum
    :type minimum: float | int
    :param maximum: Invalidate the property when value greater than specified maximum
    :type maximum: float | int
    :param exclusive_minimum: when True, it indicates that the range excludes the minimum value.
        When False (or not included), it indicates that the range includes the minimum value
    :type exclusive_minimum: bool
    :param exclusive_maximum: when True, it indicates that the range excludes the maximum value.
        When false (or not included), it indicates that the range includes the maximum value
    :type exclusive_maximum: bool
    :param multiple_of: invalidate the property when value is not multiple of specified
    :type multiple_of: float | int
    """

    MESSAGES = {
        'type': "Should be a number",
        'convert': "Couldn't convert to a number",
        'minimum': "Is less than the minimum of {0}",
        'exclusive_minimum': "Is less than or equal to the minimum of {0}",
        'maximum': "Is greater than the maximum of {0}",
        'exclusive_maximum': "Is greater than or equal to the maximum of {0}",
        'multiple_of': "Is not a multiple of {0}"

    }

    __slots__ = [
        'minimum',
        'maximum',
        'exclusive_minimum',
        'exclusive_maximum',
        'multiple_of'
    ]

    def __init__(self,
                 minimum=None,
                 maximum=None,
                 exclusive_minimum=False,
                 exclusive_maximum=False,
                 multiple_of=None,
                 **kwargs):
        self.minimum = minimum
        self.maximum = maximum
        self.exclusive_minimum = exclusive_minimum
        self.exclusive_maximum = exclusive_maximum
        self.multiple_of = multiple_of
        super(NumberType, self).__init__(**kwargs)

    def _convert(self, raw, path, strict=True, **context):
        if isinstance(raw, integer_types + (float, decimal.Decimal)):
            return raw

        if strict:
            raise SchemaError(Error(path, self.messages['type']))

        try:
            return float(raw)
        except (ValueError, TypeError):
            raise SchemaError(Error(path, self.messages['convert']))

    def validate_minimum(self, converted, raw):
        if self.minimum is not None:
            if self.exclusive_minimum and converted <= self.minimum:
                return self.messages['exclusive_minimum'].format(self.minimum)

            if not self.exclusive_minimum and converted < self.minimum:
                return self.messages['minimum'].format(self.minimum)

    def validate_maximum(self, converted, raw):
        if self.maximum is not None:
            if self.exclusive_maximum and converted >= self.maximum:
                return self.messages['exclusive_maximum'].format(self.maximum)

            if not self.exclusive_maximum and converted > self.maximum:
                return self.messages['maximum'].format(self.maximum)

    def validate_multiple_of(self, converted, raw):
        if self.multiple_of is not None:
            if isinstance(self.multiple_of, float):
                quotient = converted / self.multiple_of
                failed = int(quotient) != quotient
            else:
                failed = converted % self.multiple_of

            if failed:
                return self.messages['multiple_of'].format(self.multiple_of)


class IntegerType(NumberType):

    """Integer type"""

    MESSAGES = {
        'type': "Should be an integer",
        'convert': "Couldn't convert to an integer"
    }

    __slots__ = []

    def _convert(self, raw, path, strict=True, **context):
        if isinstance(raw, integer_types):
            return raw

        if strict:
            raise SchemaError(Error(path, self.messages['type']))

        try:
            return int(raw)
        except (TypeError, ValueError):
            raise SchemaError(Error(path, self.messages['convert']))


class BooleanType(AbstractType):

    """Boolean type"""

    MESSAGES = {
        'type': "Should be a boolean",
        'convert': "Couldn't convert to a boolean"
    }

    __slots__ = []

    def _convert(self, raw, path, strict=True, **context):
        if isinstance(raw, bool):
            return raw

        if strict:
            raise SchemaError(Error(path, self.messages['type']))

        if isinstance(raw, string_types):
            try:
                return bool(strtobool(raw))
            except ValueError:
                pass

        elif isinstance(raw, integer_types + (float, )):
            return bool(raw)

        raise SchemaError(Error(path, self.messages['convert']))


class DateType(AbstractType):

    """Date type

    Converts RFC3339 full-date string into python date object

    """

    MESSAGES = {
        'type': "Should be a string",
        'convert': "Is not a valid RFC3339 full-date"
    }

    __slots__ = []

    def _convert(self, raw, path, **context):
        if isinstance(raw, datetime.date):
            return raw

        if not isinstance(raw, string_types):
            raise SchemaError(Error(path, self.messages['type']))

        try:
            return datetime.datetime.strptime(raw, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            raise SchemaError(Error(path, self.messages['convert']))


class DateTimeType(AbstractType):

    """Datetime type

    Converts RFC3339 date-time string into python datetime object

    """

    MESSAGES = {
        'type': "Should be a string",
        'convert': "Is not a valid RFC3339 date-time"
    }

    __slots__ = []

    def _convert(self, raw, path, **context):
        if isinstance(raw, datetime.datetime):
            return raw

        if not isinstance(raw, string_types):
            raise SchemaError(Error(path, self.messages['type']))

        try:
            return datetime.datetime.fromtimestamp(rfc3339_to_timestamp(raw))
        except (InvalidRFC3339Error, ValueError, TypeError):
            raise SchemaError(Error(path, self.messages['convert']))


class PatternType(AbstractType):

    """Pattern type"""

    MESSAGES = {
        'type': "Should be a string",
        'convert': "Invalid regular expression"
    }

    __slots__ = []

    def _convert(self, raw, path, **context):
        if not isinstance(raw, string_types):
            raise SchemaError(Error(path, self.messages['type']))

        try:
            return re.compile(raw)
        except (TypeError, re.error):
            raise SchemaError(Error(path, self.messages['convert']))


class UriType(StringType):

    """Url type"""

    MESSAGES = {
        'invalid': "Is not a valid URI according to RFC3987"
    }

    __slots__ = []

    def validate_format(self, converted, raw):
        try:
            rfc3987.parse(converted, rule='URI')
        except ValueError:
            return self.messages['invalid']


EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


class EmailType(StringType):

    """Email type"""

    MESSAGES = {
        'invalid': "Is not a valid email"
    }

    __slots__ = []

    def validate_format(self, converted, raw):
        if not EMAIL_PATTERN.match(converted):
            return self.messages['invalid']


class Int32Type(IntegerType):

    """Int32 type"""

    MESSAGES = {
        'invalid': "Is not a valid int32"
    }

    __slots__ = []

    def validate_format(self, converted, raw):
        if converted < -2147483648 or converted > 2147483647:
            return self.messages['invalid']


class Int64Type(IntegerType):

    """Int64 type"""

    MESSAGES = {
        'invalid': "Is not a valid int64"
    }

    __slots__ = []

    def validate_format(self, converted, raw):
        if converted < -9223372036854775808 or converted > 9223372036854775807:
            return self.messages['invalid']


UUID_PATTERN = re.compile(
    '^'
    '[a-f0-9]{8}-'
    '[a-f0-9]{4}-'
    '[1345][a-f0-9]{3}-'
    '[a-f0-9]{4}'
    '-[a-f0-9]{12}'
    '$'
)


class UUIDType(AbstractType):

    """UUID type"""

    MESSAGES = {
        'type': "Should be a string",
        'invalid': "Is not a valid UUID"
    }

    __slots__ = []

    def _convert(self, raw, path, **context):
        if isinstance(raw, string_types):
            return raw

        raise SchemaError(Error(path, self.messages['type']))

    def validate_format(self, converted, raw):
        if not UUID_PATTERN.match(converted):
            return self.messages['invalid']


BASE64_PATTERN = re.compile(r'^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$')


class Base64Type(AbstractType):

    """Base64 type"""

    MESSAGES = {
        'type': "Should be a base64 encoded string or a file-like object"
    }

    __slots__ = []

    def _convert(self, raw, path, **context):
        if isinstance(raw, (Base64DecodableStream, Base64EncodableStream)):
            return raw

        if isinstance(raw, string_types) and BASE64_PATTERN.match(raw):
            return Base64DecodableStream(StringIO(raw))

        elif is_flo(raw):
            return Base64DecodableStream(raw)

        else:
            raise SchemaError(Error(path, self.messages['type']))


class BinaryType(AbstractType):

    """Binary type"""

    MESSAGES = {
        'type': "Should be a string or a file-like object"
    }

    __slots__ = []

    def _convert(self, raw, path, **context):
        if isinstance(raw, string_types):
            return StringIO(raw)

        elif is_flo(raw):
            return raw

        raise SchemaError(Error(path, self.messages['type']))


class ArrayType(AbstractType):

    """Array type

    :param item_type: type of items
    :type item_type: AbstractConvertible
    :param min_items: invalidate property when value length less than specified
    :type min_items: int
    :param max_items: invalidate property when value length more than specified
    :type max_items: int
    :param unique_items: shows that each of the items in an array must be unique
    :type unique_items: bool
    :param unique_item_properties: allows to check that some properties in array items are unique
    :type unique_item_properties: list of basestring
    """

    MESSAGES = {
        'type': "Should be a list or a tuple",
        'min_items': "Array must have at least {0} items. It had only {1} items",
        'max_items': "Array must have no more than {0} items. It had {1} items",
        'unique_items': "Has non-unique items",
        'unique_item_properties': "All items must be a mapping"
    }

    __slots__ = [
        'item_type',
        'min_items',
        'max_items',
        'unique_items',
        'unique_item_properties'
    ]

    def __init__(self,
                 item_type,
                 min_items=None,
                 max_items=None,
                 unique_items=False,
                 unique_item_properties=None,
                 **kwargs):
        self.item_type = item_type
        self.min_items = min_items
        self.max_items = max_items
        self.unique_items = unique_items
        self.unique_item_properties = unique_item_properties
        super(ArrayType, self).__init__(**kwargs)

    def _convert(self, raw, path, **context):
        if not isinstance(raw, (list, tuple)):
            raise SchemaError(Error(path, self.messages['type']))

        result = []
        errors = []
        for i, item in enumerate(raw):
            try:
                result.append(self.item_type.convert(item, path / i, **context))
            except SchemaError as e:
                errors.extend(e.errors)

        if errors:
            raise SchemaError(*errors)

        return result

    def validate_length(self, converted, raw):
        length = len(converted)

        if self.min_items is not None and length < self.min_items:
            return self.messages['min_items'].format(self.min_items, length)

        if self.max_items is not None and length > self.max_items:
            return self.messages['max_items'].format(self.max_items, length)

    def validate_uniqueness(self, converted, raw):
        if not self.unique_items:
            return

        items = converted
        if self.unique_item_properties:
            if not all(isinstance(item, Mapping) for item in converted):
                return self.messages['unique_item_properties']

            items = [tuple(item.get(k) for k in self.unique_item_properties) for item in converted]

        if not uniq(items):
            return self.messages['unique_items']


class MapType(AbstractType):

    """Map type

    :param value_type: type of map values
    :type value_type: AbstractConvertible
    :param min_values: invalidate dictionary when number of values less than specified
    :type min_values: int
    :param max_values: invalidate dictionary when number of values more than specified
    :type max_values: int
    """

    MESSAGES = {
        'type': "Should be a mapping",
        'min_values': "Map must have at least {0} values. It had only {1} values",
        'max_values': "Map must have no more than {0} values. It had {1} values",
    }

    __slots__ = [
        'value_type',
        'min_values',
        'max_values'
    ]

    def __init__(self, value_type, min_values=None, max_values=None, **kwargs):
        self.value_type = value_type
        self.min_values = min_values
        self.max_values = max_values
        super(MapType, self).__init__(**kwargs)

    def _convert(self, raw, path, **context):
        if not isinstance(raw, Mapping):
            raise SchemaError(Error(path, self.messages['type']))

        result = {}
        errors = []
        for key, value in sorted(iteritems(raw)):
            try:
                result[key] = self.value_type.convert(value, path / key, **context)
            except SchemaError as e:
                errors.extend(e.errors)

        if errors:
            raise SchemaError(*errors)

        return result

    def validate_length(self, converted, raw):
        length = len(converted)

        if self.min_values is not None and length < self.min_values:
            return self.messages['min_values'].format(self.min_values, length)

        if self.max_values is not None and length > self.max_values:
            return self.messages['max_values'].format(self.max_values, length)


class DiscriminatorType(AbstractType):

    """Discriminator type

    :param property_name: property name that decides target type
    :type property_name: basestring
    :param mapping: mapping of extracted values to target types
    :type mapping: dict[basestring, AbstractConvertible]
    """

    MESSAGES = {
        'type': "Should be a mapping",
        'not_present': "A property with name '{0}' must be present",
        'not_match': "The discriminator value should be equal to one of the following values: {0}"
    }

    __slots__ = [
        'property_name',
        'mapping'
    ]

    def __init__(self, property_name, mapping, **kwargs):
        self.property_name = property_name
        self.mapping = mapping
        super(DiscriminatorType, self).__init__(**kwargs)

    def _convert(self, raw, path, **context):
        if not isinstance(raw, Mapping):
            raise SchemaError(Error(path, self.messages['type']))

        if self.property_name not in raw:
            raise SchemaError(Error(path, self.messages['not_present'].format(self.property_name)))

        matched_type = self.mapping.get(raw[self.property_name])

        if matched_type is None:
            raise SchemaError(
                Error(path, self.messages['not_match'].format(', '.join(sorted(map(str, iterkeys(self.mapping)))))))

        return matched_type.convert(raw, path, **context)


class AllOfType(AbstractType):

    """AllOf type

    The given data must be valid against all of the given subschemas

    :param subtypes: types for which the given data must be valid
    :type subtypes: list of AbstractConvertible
    """

    MESSAGES = {
        'not_all': "Does not match all schemas from `allOf`. Invalid schema indexes: {0}"
    }

    __slots__ = [
        'subtypes'
    ]

    def __init__(self, subtypes, **kwargs):
        self.subtypes = subtypes
        super(AllOfType, self).__init__(**kwargs)

    def _convert(self, raw, path, **context):
        matched = []
        not_matched_indexes = []
        errors = []
        for i, subtype in enumerate(self.subtypes):
            try:
                matched.append(subtype.convert(raw, path / i, **context))
            except SchemaError as e:
                errors.extend(e.errors)
                not_matched_indexes.append(i)
                continue

        if errors:
            raise SchemaError(
                Error(path, self.messages['not_all'].format(', '.join(sorted(map(str, not_matched_indexes))))), *errors)

        if all(isinstance(value, Mapping) for value in matched):
            matched.insert(0, Object())
            return reduce(operator.or_, matched)

        if all(isinstance(value, (list, tuple)) for value in matched):
            result = []
            for squashed in zip(matched):
                if all(isinstance(value, Mapping) for value in squashed):
                    result.append(reduce(operator.or_, (Object(), ) + squashed))
                else:
                    result.append(squashed[-1])
            return result

        return matched[-1]


class AnyOfType(AbstractType):

    """AnyOf type

    The given data must be valid against any (one or more) of the given subschemas

    :param subtypes: types for which the given data must be valid
    :type subtypes: list of AbstractConvertible
    """

    MESSAGES = {
        'not_any': "Does not match any schemas from `anyOf`"
    }

    __slots__ = [
        'subtypes'
    ]

    def __init__(self, subtypes, **kwargs):
        self.subtypes = subtypes
        super(AnyOfType, self).__init__(**kwargs)

    def _convert(self, raw, path, **context):
        matched = []
        errors = []
        for i, subtype in enumerate(self.subtypes):
            try:
                matched.append(subtype.convert(raw, path / i, **context))
            except SchemaError as e:
                errors.extend(e.errors)
                continue

        if not matched:
            raise SchemaError(Error(path, self.messages['not_any']), *errors)

        if all(isinstance(value, Mapping) for value in matched):
            matched.append(Object())
            return reduce(operator.or_, reversed(matched))

        return matched[0]


class OneOfType(AbstractType):

    """OneOf type

    The given data must be valid against exactly one of the given subschemas

    :param subtypes: types for which the given data must be valid
    :type subtypes: list of AbstractConvertible
    """

    MESSAGES = {
        'no_one': "Is valid against no schemas from `oneOf`",
        'ambiguous': "Is valid against more than one schema from `oneOf`. Valid schema indexes: {0}"
    }

    __slots__ = [
        'subtypes'
    ]

    def __init__(self, subtypes, **kwargs):
        self.subtypes = subtypes
        super(OneOfType, self).__init__(**kwargs)

    def _convert(self, raw, path, **context):
        matched = []
        matched_indexes = []
        errors = []
        for i, subtype in enumerate(self.subtypes):
            try:
                matched.append(subtype.convert(raw, path / i, **context))
                matched_indexes.append(i)
            except SchemaError as e:
                errors.extend(e.errors)

        if not matched:
            raise SchemaError(Error(path, self.messages['no_one']), *errors)

        elif len(matched) > 1:
            raise SchemaError(
                Error(path, self.messages['ambiguous'].format(', '.join(sorted(map(str, matched_indexes))))))

        return matched[0]


class NotType(AbstractType):

    """Not type

    Declares that a instance validates if it doesn't validate against the given subschemas

    :param subtypes: types for which the given data must not be valid
    :type subtype: list of AbstractConvertible
    """

    MESSAGES = {
        'not_acceptable': "Not acceptable data"
    }

    __slots__ = [
        'subtypes'
    ]

    def __init__(self, subtypes, **kwargs):
        self.subtypes = subtypes
        super(NotType, self).__init__(**kwargs)

    def _convert(self, raw, path, **context):
        for i, subtype in enumerate(self.subtypes):
            try:
                subtype.convert(raw, path / i, **context)
            except SchemaError:
                pass
            else:
                raise SchemaError(Error(path, self.messages['not_acceptable']))

        return raw


class ObjectTypeMeta(TypeMeta):

    def __new__(mcs, name, bases, attrs):
        properties = {}
        required = set()
        pattern_properties = {}
        additional_properties = True

        for base in reversed(bases):
            if hasattr(base, 'PROPERTIES'):
                properties.update(base.PROPERTIES)

            if hasattr(base, 'REQUIRED'):
                required.update(base.REQUIRED)

            if hasattr(base, 'PATTERN_PROPERTIES'):
                pattern_properties.update(base.PATTERN_PROPERTIES)

            if hasattr(base, 'ADDITIONAL_PROPERTIES'):
                additional_properties = base.ADDITIONAL_PROPERTIES

        if 'PROPERTIES' in attrs:
            properties.update(attrs['PROPERTIES'])

        if 'REQUIRED' in attrs:
            required.update(attrs['REQUIRED'])

        if 'PATTERN_PROPERTIES' in attrs:
            pattern_properties.update(attrs['PATTERN_PROPERTIES'])

        if 'ADDITIONAL_PROPERTIES' in attrs:
            additional_properties = attrs['ADDITIONAL_PROPERTIES']

        klass = TypeMeta.__new__(mcs, name, bases, attrs)

        klass.PROPERTIES = properties
        klass.REQUIRED = required
        klass.PATTERN_PROPERTIES = pattern_properties
        klass.ADDITIONAL_PROPERTIES = additional_properties

        return klass


class ObjectType(with_metaclass(ObjectTypeMeta, AbstractType)):

    """Object type

    :param properties: is a dictionary, where each key is the name of a property and each value
        is a type used to validate that property
    :type properties: dict[basestring, AbstractType]
    :param required: by default, the properties defined by the `properties` are not required.
        However, one can provide a list of required properties using the `required`. The `required`
        takes an array of one or more strings
    :type required: tuple | list | set
    :param pattern_properties: it is map from regular expressions to types. If an additional
        property matches a given regular expression, it must also validate against the
        corresponding type
    :type pattern_properties: dict[re._pattern_type, AbstractType]
    :param additional_properties: is used to control the handling of extra stuff, that is,
        properties whose names are not listed in the properties. If is `True` then possible
        any additional properties, that not listed in `properties`. If is `False` then
        additional properties not allowed. If is a `AbstractType` then additional properties
        of this type are allowed. By default any additional properties are allowed
    :type additional_properties: bool | AbstractType
    :param min_properties: invalidate object when number of properties less than specified
    :param max_properties: invalidate object when number of properties more than specified
    """

    MESSAGES = {
        'type': "Should be a mapping",
        'required': "The following required properties are missed: {0}",
        'extra_properties': (
            "No unspecified properties are allowed."
            " The following unspecified properties were found: {0}"
        ),
        'min_properties': "Object must have at least {0} properties. It had only {1} properties",
        'max_properties': "Object must have no more than {0} properties. It had {1} properties",
    }

    __slots__ = [
        'properties',
        'required',
        'pattern_properties',
        'additional_properties',
        'min_properties',
        'max_properties'
    ]

    def __init__(self,
                 properties=None,
                 required=None,
                 pattern_properties=None,
                 additional_properties=None,
                 min_properties=None,
                 max_properties=None,
                 **kwargs):
        self.properties = dict(self.PROPERTIES, **(properties or {}))
        self.required = set.union(self.REQUIRED, set(required or []))
        self.pattern_properties = dict(self.PATTERN_PROPERTIES, **(pattern_properties or {}))

        self.additional_properties = self.ADDITIONAL_PROPERTIES
        if additional_properties is not None:
            self.additional_properties = additional_properties

        self.min_properties = min_properties
        self.max_properties = max_properties
        super(ObjectType, self).__init__(**kwargs)

    def _convert(self, raw, path, **context):
        if not isinstance(raw, Mapping):
            raise SchemaError(Error(path, self.messages['type']))

        errors = []
        result = Object()

        missed_properties = []
        for required_property in self.required:
            if required_property not in raw:
                missed_properties.append(required_property)

        if missed_properties:
            errors.append(Error(path, self.messages['required'].format(', '.join(sorted(missed_properties)))))

        extra_properties = set(raw) - set(self.properties)
        matched = []
        for extra_property in extra_properties:
            for pattern, prop in iteritems(self.pattern_properties):
                if pattern.match(extra_property):
                    matched.append(extra_property)
                    try:
                        result.pattern_properties[extra_property] = prop.convert(
                            raw[extra_property], path / extra_property, **context)
                    except SchemaError as e:
                        errors.extend(e.errors)

                    break

            if extra_property in matched:
                continue

            if self.additional_properties is True:
                result.additional_properties[extra_property] = raw[extra_property]

                matched.append(extra_property)

            elif isinstance(self.additional_properties, AbstractConvertible):
                try:
                    result.additional_properties[extra_property] = self.additional_properties.convert(
                        raw[extra_property], path / extra_property, **context)
                except SchemaError as e:
                    errors.extend(e.errors)
                else:
                    matched.append(extra_property)

        extra_properties = extra_properties - set(matched)
        if extra_properties:
            errors.append(
                Error(path, self.messages['extra_properties'].format(', '.join(sorted(extra_properties)))))

        for prop_name, prop in iteritems(self.properties):
            try:
                if prop_name not in raw and prop_name in self.required:
                    continue

                converted = prop.convert(raw.get(prop_name, Undefined), path / prop_name, **context)

                if converted is not Undefined:
                    result.properties[prop_name] = converted

            except SchemaError as e:
                errors.extend(e.errors)
                continue

        if errors:
            raise SchemaError(*errors)

        return result

    def validate_length(self, converted, raw):
        length = len(raw)

        if self.min_properties is not None and length < self.min_properties:
            return self.messages['min_properties'].format(self.min_properties, length)

        if self.max_properties is not None and length > self.max_properties:
            return self.messages['max_properties'].format(self.max_properties, length)


class LazyType(AbstractConvertible):

    """Lazy type

    Resolves target type when it needed

    :param resolver: callable for lazy resolving of target type
    :type resolver: callable
    """

    def __init__(self, resolver, **kwargs):
        self.resolver = resolver
        super(LazyType, self).__init__(**kwargs)

    @cached_property
    def resolved(self):
        return self.resolver()

    def convert(self, raw, path, **context):
        return self.resolved.convert(raw, path, **context)
