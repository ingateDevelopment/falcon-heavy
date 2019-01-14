from __future__ import unicode_literals, absolute_import

import re
import datetime
import weakref
import operator
from collections import OrderedDict
from distutils.util import strtobool
from contextlib import contextmanager

import rfc3987
import strict_rfc3339

from six import string_types, text_type, iteritems, with_metaclass
from six.moves import StringIO, reduce

from ..utils import (
    coalesce,
    Base64EncodableStream,
    Base64DecodableStream
)
from .compat import ChainMap, Mapping
from .cursor import Cursor
from .utils import uniq, prepare_validator, is_file_like
from .undefined import Undefined
from .exceptions import (
    SchemaError,
    UnmarshallingError,
    ValidationError,
    PolymorphicError,
    DiscriminatorError
)


class Object(ChainMap):

    """Object representation.

    :param url: Uri where the object was obtained.
    """

    def __init__(self, url):
        self.url = url
        super(Object, self).__init__({}, {}, {}, {})

    @property
    def changes(self):
        return self.maps[0]

    @property
    def properties(self):
        return self.maps[1]

    @property
    def pattern_properties(self):
        return self.maps[2]

    @property
    def additional_properties(self):
        return self.maps[3]

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
        return repr(dict(self))

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

    @staticmethod
    def from_file(schema, path, strict=True, resolver_handlers=None):
        return ObjectType(schema).unmarshal(
            Cursor.from_file(path, resolver_handlers=resolver_handlers),
            context=Context(strict=strict)
        )

    @staticmethod
    def from_raw(schema, raw, strict=True, resolver_handlers=None):
        return ObjectType(schema).unmarshal(
            Cursor.from_raw(raw, resolver_handlers=resolver_handlers),
            context=Context(strict=strict)
        )


class Context(object):

    def __init__(self, strict=True):
        self.strict = strict
        self.registry = {}

    @contextmanager
    def in_scope(self):
        old_strict = self.strict
        try:
            yield
        finally:
            self.strict = old_strict


class TypeMeta(type):

    def __new__(mcs, name, bases, attrs):
        messages = {}
        validators = OrderedDict()

        for base in reversed(bases):
            if hasattr(base, 'MESSAGES'):
                messages.update(base.MESSAGES)

            if hasattr(base, "VALIDATORS"):
                validators.update(base.VALIDATORS)

        if 'MESSAGES' in attrs:
            messages.update(attrs['MESSAGES'])

        for attr_name, attr in attrs.items():
            if attr_name.startswith("validate_"):
                validators[attr_name] = 1
                attrs[attr_name] = prepare_validator(attr, 2)

        klass = type.__new__(mcs, name, bases, attrs)
        klass.MESSAGES = messages
        klass.VALIDATORS = validators

        return klass


class AbstractUnmarshallable(object):

    __slots__ = [
        '__weakref__'
    ]

    def unmarshal(self, cursor, context=None):
        raise NotImplementedError


class AbstractType(with_metaclass(TypeMeta, AbstractUnmarshallable)):

    """Abstract class of property types.

    :param required:
        Invalidate property when value is not supplied. Default: False.
    :param nullable:
        Invalidate property when value is None. Default: False.
    :param default:
        Provide default value. Default: Undefined.
    :param validators:
        A list of callables. Each callable receives the value after it has been
        unmarshalled. Default: None
    :param enum:
        Provide possible property values.
    :param strict:
        Indicates that the property value type must match exactly the property type.
        Strict value propagate to all nested properties. Default: None.
    :param messages:
        Override the error messages with a dict. You can also do this by
        subclassing the Type and defining a `MESSAGES` dict attribute on the
        class. A metaclass will merge all the `MESSAGES` and override the
        resulting dict with instance level `messages` and assign to
        `self.messages`.
    :param preprocessor:
        Callable that may modify value before unmarshalling and validation.
    :param postprocessor:
        Callable that may modify value after unmarshalling and validation.
    """

    MESSAGES = {
        'enum': "Value is invalid. Expected one of: {0}",
        'required': "Missing value of required property",
        'null': "Property not allow null values",
    }

    __slots__ = [
        'required',
        'nullable',
        'default',
        'validators',
        'enum',
        'strict',
        'messages',
        'preprocessor',
        'postprocessor'
    ]

    def __init__(self,
                 required=False,
                 nullable=False,
                 default=Undefined,
                 validators=None,
                 enum=None,
                 strict=None,
                 messages=None,
                 preprocessor=None,
                 postprocessor=None):
        self.required = required
        self.nullable = nullable
        self.default = default
        self.validators = [getattr(self, validator_name) for validator_name in self.VALIDATORS]
        if validators:
            for validator in validators:
                assert callable(validator), "Validator MUST be a callable"
            self.validators.extend([prepare_validator(validator, 2) for validator in validators])
        self.enum = tuple(enum) if enum is not None else None
        self.strict = strict
        self.messages = dict(self.MESSAGES, **(messages or {}))
        assert preprocessor is None or callable(preprocessor), "Preprocessor MUST be a callable"
        self.preprocessor = preprocessor
        assert postprocessor is None or callable(postprocessor), "Postprocessor MUST be a callable"
        self.postprocessor = postprocessor

    def validate_enum(self, value):
        if self.enum and value not in self.enum:
            raise ValidationError(
                self.messages['enum'].format(', '.join(map(str, self.enum))))

    def _validate(self, value):
        errors = []
        for validator in self.validators:
            try:
                validator(value)
            except ValidationError as e:
                errors.extend(e.errors)
        if errors:
            raise ValidationError(errors)

        return value

    def _unmarshal(self, cursor, context):
        raise NotImplementedError

    def unmarshal(self, cursor, context=None):
        context = context or Context()

        if self.preprocessor is not None:
            cursor.value = self.preprocessor(cursor.value)

        if cursor.is_undefined and self.required:
            raise UnmarshallingError(self.messages['required'])

        if cursor.is_undefined and self.default is not Undefined:
            cursor.value = self.default

        if cursor.is_null and not self.nullable:
            raise UnmarshallingError(self.messages['null'])

        if cursor.is_null or cursor.is_undefined:
            return cursor.value

        with context.in_scope():
            context.strict = coalesce(self.strict, context.strict)
            unmarshalled = self._validate(self._unmarshal(cursor, context))

        if self.postprocessor is not None:
            unmarshalled = self.postprocessor(unmarshalled)

        return unmarshalled


class AnyType(AbstractType):

    __slots__ = []

    def _unmarshal(self, cursor, context):
        return cursor.value


class StringType(AbstractType):

    """String property type.

    :param min_length: Invalidate property when value length less than specified. Default: None.
    :param max_length: Invalidate property when value length more than specified. Default: None.
    :param pattern: Compiled regular expression. Invalidate property when value is not match
        to this pattern. Default: None.
    """

    MESSAGES = {
        'unmarshal': "Couldn't interpret value as string",
        'min_length': "Value length is lower than {0} symbols",
        'max_length': "Value length is greater than {0} symbols",
        'pattern': "Value did not match to pattern"
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

    def _unmarshal(self, cursor, context):
        if cursor.is_string:
            return cursor.value

        if context.strict:
            raise UnmarshallingError(self.messages['unmarshal'])

        try:
            return text_type(cursor.value)
        except (TypeError, ValueError):
            raise UnmarshallingError(self.messages['unmarshal'])

    def validate_length(self, value):
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(self.messages['min_length'].format(self.min_length))

        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(self.messages['max_length'].format(self.max_length))

    def validate_pattern(self, value):
        if self.pattern is not None and self.pattern.match(value) is None:
            raise ValidationError(self.messages['pattern'])


class AbstractNumberType(AbstractType):

    """Abstract number property type.

    :param minimum: Specifies a minimum numeric value. Default: None.
    :param maximum: Specifies a maximum numeric value. Default: None.
    :param exclusive_minimum: When True, it indicates that the range excludes the minimum value.
        When False (or not included), it indicates that the range includes the minimum value.
        Default: False.
    :param exclusive_maximum: When True, it indicates that the range excludes the maximum value.
        When false (or not included), it indicates that the range includes the maximum value.
        Default: False.
    :param multiple_of: Shows that value must be the multiple of a given number. Default: None.
    """

    MESSAGES = {
        'minimum': "Value is lower than {0}",
        'exclusive_minimum': "Value is not greater than {0}",
        'maximum': "Value is greater than {0}",
        'exclusive_maximum': "Value is not lower than {0}",
        'multiple_of': "Value is not a multiple of {0}",
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
        assert multiple_of != 0, "Value can't be a multiple of zero"
        self.multiple_of = multiple_of
        super(AbstractNumberType, self).__init__(**kwargs)

    def validate_range(self, value):
        if self.minimum is not None:
            if self.exclusive_minimum and value <= self.minimum:
                raise ValidationError(self.messages['exclusive_minimum'].format(self.minimum))
            if not self.exclusive_minimum and value < self.minimum:
                raise ValidationError(self.messages['minimum'].format(self.minimum))

        if self.maximum is not None:
            if self.exclusive_maximum and value >= self.maximum:
                raise ValidationError(self.messages['exclusive_maximum'].format(self.maximum))
            if not self.exclusive_maximum and value > self.maximum:
                raise ValidationError(self.messages['maximum'].format(self.maximum))

    def validate_multiple_of(self, value):
        if self.multiple_of is None:
            return

        if isinstance(self.multiple_of, float):
            quotient = value / self.multiple_of
            failed = int(quotient) != quotient
        else:
            failed = value % self.multiple_of

        if failed:
            raise ValidationError(self.messages['multiple_of'].format(self.multiple_of))


class IntegerType(AbstractNumberType):

    """Integer property type."""

    MESSAGES = {
        'unmarshal': "Couldn't interpret value as integer",
    }

    __slots__ = []

    def _unmarshal(self, cursor, context):
        if cursor.is_integer:
            return cursor.value

        if context.strict:
            raise UnmarshallingError(self.messages['unmarshal'])

        try:
            return int(cursor.value)
        except (TypeError, ValueError):
            raise UnmarshallingError(self.messages['unmarshal'])


class FloatType(AbstractNumberType):

    """Float property type."""

    MESSAGES = {
        'unmarshal': "Couldn't interpret value as float",
    }

    __slots__ = []

    def _unmarshal(self, cursor, context):
        if cursor.is_number:
            return cursor.value

        if context.strict:
            raise UnmarshallingError(self.messages['unmarshal'])

        try:
            return float(cursor.value)
        except (TypeError, ValueError):
            raise UnmarshallingError(self.messages['unmarshal'])


class BooleanType(AbstractType):

    """Boolean property type."""

    MESSAGES = {
        'unmarshal': "Couldn't interpret value as boolean",
    }

    __slots__ = []

    def _unmarshal(self, cursor, context):
        if cursor.is_boolean:
            return cursor.value

        if not context.strict:
            if cursor.is_string:
                return bool(strtobool(cursor.value))
            elif cursor.is_integer and cursor.value in (0, 1):
                return int == 1
            elif cursor.is_number:
                return cursor.value != 0

        raise UnmarshallingError(self.messages['unmarshal'])


class DateType(AbstractType):

    """Date property type. Convert RFC3339 full-date string into python date object."""

    MESSAGES = {
        'unmarshal': "Couldn't interpret value as date",
    }

    __slots__ = []

    def _unmarshal(self, cursor, context):
        if isinstance(cursor.value, datetime.date):
            return cursor.value

        try:
            return datetime.datetime.strptime(cursor.value, '%Y-%m-%d').date()
        except Exception:
            raise UnmarshallingError(self.messages['unmarshal'])


class DateTimeType(AbstractType):

    """Datetime property type. Convert RFC3339 date-time string into python datetime object."""

    MESSAGES = {
        'unmarshal': "Couldn't interpret value as date-time",
    }

    __slots__ = []

    def _unmarshal(self, cursor, context):
        if isinstance(cursor.value, datetime.datetime):
            return cursor.value

        try:
            return datetime.datetime.fromtimestamp(
                strict_rfc3339.rfc3339_to_timestamp(cursor.value))
        except Exception:
            raise UnmarshallingError(self.messages['unmarshal'])


class PatternType(StringType):

    """Pattern property type."""

    __slots__ = []

    def _unmarshal(self, cursor, context):
        value = super(PatternType, self)._unmarshal(cursor, context)
        return re.compile(value)


class UrlType(StringType):

    """Url property type."""

    MESSAGES = {
        'format': "Is not valid url"
    }

    __slots__ = []

    def validate_format(self, value):
        try:
            rfc3987.parse(value, rule='URI')
        except ValueError:
            raise ValidationError(self.messages['format'])


class EmailType(StringType):

    """Email property type."""

    MESSAGES = {
        'format': "Is not valid email"
    }

    __slots__ = []

    def validate_format(self, value):
        if "@" not in value:
            raise ValidationError(self.messages['format'])


class Int32Type(IntegerType):

    """Int32 property type."""

    MESSAGES = {
        'format': "Is not valid int32"
    }

    __slots__ = []

    def validate_format(self, value):
        if value < -2147483648 or value > 2147483647:
            raise ValidationError(self.messages['format'])


class Int64Type(IntegerType):

    """Int64 property type."""

    MESSAGES = {
        'format': "Is not valid int64"
    }

    __slots__ = []

    def validate_format(self, value):
        if value < -9223372036854775808 or value > 9223372036854775807:
            raise ValidationError(self.messages['format'])


UUID_PATTERN = re.compile(
    '^'
    '[a-f0-9]{8}-'
    '[a-f0-9]{4}-'
    '[1345][a-f0-9]{3}-'
    '[a-f0-9]{4}'
    '-[a-f0-9]{12}'
    '$'
)


class UUIDType(StringType):

    """UUID property type."""

    MESSAGES = {
        'format': "Is not valid UUID"
    }

    __slots__ = []

    def validate_format(self, value):
        if not UUID_PATTERN.match(value):
            raise ValidationError(self.messages['format'])


BASE64_PATTERN = re.compile(r'^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$')


class Base64Type(AnyType):

    """Base64 property type."""

    MESSAGES = {
        'unmarshal': "Couldn't interpret value as base64 encoded"
    }

    __slots__ = []

    def _unmarshal(self, cursor, context):
        if isinstance(cursor.value, (Base64DecodableStream, Base64EncodableStream)):
            return cursor.value

        value = super(Base64Type, self)._unmarshal(cursor, context)

        if isinstance(value, string_types) and BASE64_PATTERN.match(value):
            return Base64DecodableStream(StringIO(value))

        elif is_file_like(value):
            return Base64DecodableStream(value)

        else:
            raise UnmarshallingError(self.messages['unmarshal'])


class FileType(AnyType):

    """File property type."""

    MESSAGES = {
        'unmarshal': "Couldn't interpret value as file-like object"
    }

    __slots__ = []

    def _unmarshal(self, cursor, context):
        value = super(FileType, self)._unmarshal(cursor, context)

        if is_file_like(value):
            return value

        else:
            raise UnmarshallingError(self.messages['unmarshal'])


class ArrayType(AbstractType):

    """List or tuple property type.

    :param item_types: If specified one type then target type of property is list.
        If specifies several types then target type of property is tuple.
    :param min_items: Invalidate property when value length less than specified. Default: None.
    :param max_items: Invalidate property when value length more than specified. Default: None.
    :param unique_items: Shows that each of the items in an array must be unique. Default: False.
    :param key: Key defining the primary key of the elements. Used in validating items for uniqueness.
        Default: None.
    :param additional_items: Only for tuple validation. Indicates whether the given data
        can contain additional elements. Default: True.
    """

    MESSAGES = {
        'unmarshal': "Could't interpret value as a list",
        'min_items': "List size lower than {0}",
        'max_items': "List size greater than {0}",
        'key': "Key improperly appliance",
        'uniqueness': "List items are not unique",
        'additional_items': "Additional items are not allowed",
    }

    __slots__ = [
        'item_types',
        'min_items',
        'max_items',
        'unique_items',
        'key',
        'additional_items'
    ]

    def __init__(self,
                 item_types,
                 min_items=None,
                 max_items=None,
                 unique_items=False,
                 key=None,
                 additional_items=True,
                 **kwargs):
        assert item_types, "Should be specified one or more item types"
        if not isinstance(item_types, (tuple, list)):
            self.item_types = [item_types]
        else:
            self.item_types = item_types
        assert min_items is None or min_items >= 0, "Minimum size MUST be not negative"
        assert max_items is None or max_items >= min_items or 0, (
            "Maximum size MUST be equal or greater than minimum size")
        self.min_items = min_items
        self.max_items = max_items
        self.unique_items = unique_items
        assert key is None or isinstance(key, string_types) or callable(key), (
            "Key MUST be string or callable")
        self.key = key
        self.additional_items = additional_items
        super(ArrayType, self).__init__(**kwargs)

    @property
    def _is_tuple(self):
        return len(self.item_types) > 1

    def _unmarshal_tuple(self, cursor, context):
        unmarshalled = []
        errors = {}
        for i, (value, property_type) in enumerate(zip(cursor.value, self.item_types)):
            if property_type is None:
                unmarshalled.append(value)
                continue

            try:
                with cursor.walk(i):
                    unmarshalled.append(property_type.unmarshal(
                        cursor, context=context))
            except SchemaError as e:
                errors[i] = e.errors

        if errors:
            raise UnmarshallingError(errors)

        return tuple(unmarshalled)

    def _unmarshal_array(self, cursor, context):
        unmarshalled = []
        errors = {}
        for i, item in enumerate(cursor.value):
            try:
                with cursor.walk(i):
                    unmarshalled.append(self.item_types[0].unmarshal(
                        cursor, context=context))
            except SchemaError as e:
                errors[i] = e.errors

        if errors:
            raise UnmarshallingError(errors)

        return unmarshalled

    def _unmarshal(self, cursor, context):
        if not cursor.is_array:
            raise UnmarshallingError(self.messages['unmarshal'])

        if self._is_tuple:
            return self._unmarshal_tuple(cursor, context)
        else:
            return self._unmarshal_array(cursor, context)

    def validate_size(self, value):
        if self._is_tuple:
            return

        if self.min_items is not None and len(value) < self.min_items:
            raise ValidationError(self.messages['min_items'].format(self.min_items))

        if self.max_items is not None and len(value) > self.max_items:
            raise ValidationError(self.messages['max_items'].format(self.max_items))

    def validate_uniqueness(self, value):
        if self.unique_items and not self._is_tuple:
            items = value
            if self.key is not None:
                try:
                    if isinstance(self.key, string_types):
                        items = [item.get(self.key) for item in value]
                    else:
                        items = [self.key(item) for item in value]
                except (KeyError, IndexError, AttributeError):
                    raise ValidationError(self.messages['key'])

            if not uniq(items):
                raise ValidationError(self.messages['uniqueness'])

    def validate_additional_items(self, value):
        if self._is_tuple:
            if len(value) > len(self.item_types):
                raise ValidationError(self.messages['additional_items'])


class DictType(AbstractType):

    """Dictionary property type.

    :param value_type: Type of dictionary values.
    :param min_values: Invalidate dictionary when number of values less than specified.
        Default: None.
    :param max_values: Invalidate dictionary when number of values more than specified.
        Default: None.
    """

    MESSAGES = {
        'unmarshal': "Could't interpret value as a dict",
        'min_values': "Dictionary does not have enough values",
        'max_values': "Dictionary has too many values"
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
        super(DictType, self).__init__(**kwargs)

    def _unmarshal(self, cursor, context):
        if not cursor.is_mapping:
            raise UnmarshallingError(self.messages['unmarshal'])

        unmarshalled = {}
        errors = {}
        for k, v in iteritems(cursor.value):
            try:
                with cursor.walk(k):
                    unmarshalled[k] = self.value_type.unmarshal(
                        cursor, context=context)
            except SchemaError as e:
                errors[k] = e.errors

        if errors:
            raise UnmarshallingError(errors)

        return unmarshalled

    def validate_values(self, value):
        values_count = len(value)

        if self.min_values is not None and values_count < self.min_values:
            raise ValidationError(self.messages['min_values'])

        if self.max_values is not None and values_count > self.max_values:
            raise ValidationError(self.messages['max_values'])


class Discriminator(object):

    """
    The discriminator object.
    Serves for unambiguous determination of the target property type.

    :param property_name: Property name that decides target type.
    :param mapping: Mapping of extracted values to target types.
    """

    __slots__ = [
        'property_name',
        'mapping'
    ]

    def __init__(self, property_name, mapping=None):
        self.property_name = property_name
        self.mapping = mapping

    def match(self, property_types, cursor):
        if not cursor.is_mapping:
            raise DiscriminatorError(
                "Value MUST be a mapping if discriminator specified")

        property_value = None
        with cursor.walk(self.property_name, Undefined):
            if cursor.is_undefined:
                raise DiscriminatorError(
                    "Could't discriminate type. "
                    "Property with name `{}` not found".format(
                        self.property_name))

            try:
                property_value = text_type(cursor.value)
            except (ValueError, TypeError):
                raise DiscriminatorError(
                    "Discriminator value cannot cast to string")

        matched_property_type = None
        if self.mapping is not None:
            matched_property_type = self.mapping.get(property_value)

        if matched_property_type is None:
            for property_type in property_types:
                if isinstance(property_type, ObjectType) and property_type.schema.name == property_value:
                    matched_property_type = property_type
                    break

        if matched_property_type is None:
            raise DiscriminatorError("No one of property types are "
                                     "not matched to discriminator value")

        return matched_property_type


class AllOfType(AbstractType):

    """The given data must be valid against all of the given subschemas.

    :param property_types: Types for which the given data must be valid.
    """

    __slots__ = [
        'property_types'
    ]

    def __init__(self, property_types, **kwargs):
        self.property_types = property_types
        super(AllOfType, self).__init__(**kwargs)

    def _unmarshal(self, cursor, context):
        matched = []
        errors = []
        for i, property_type in enumerate(self.property_types):
            assert isinstance(property_type, AbstractType)
            try:
                with cursor.in_scope(i):
                    matched.append(property_type.unmarshal(
                        cursor, context=context))
            except SchemaError as e:
                errors.append(e.errors)
                continue

        if errors:
            raise PolymorphicError({'__all__': errors})

        if all(isinstance(value, Mapping) for value in matched):
            matched.insert(0, Object(cursor.url))
            return reduce(operator.or_, matched)

        return matched[-1]


class AnyOfType(AbstractType):

    """The given data must be valid against any (one or more) of the given subschemas.

    :param property_types: Types for which the given data must be valid.
    :param discriminator: Discriminator object.
    """

    __slots__ = [
        'property_types',
        'discriminator'
    ]

    def __init__(self, property_types, discriminator=None, **kwargs):
        self.property_types = property_types
        assert discriminator is None or isinstance(discriminator, Discriminator), (
            "Invalid discriminator object")
        self.discriminator = discriminator
        super(AnyOfType, self).__init__(**kwargs)

    def _unmarshal(self, cursor, context):
        if self.discriminator is None:
            matched = []
            errors = []
            for i, candidate in enumerate(self.property_types):
                assert isinstance(candidate, AbstractType)
                try:
                    with cursor.in_scope(i):
                        matched.append(candidate.unmarshal(
                            cursor, context=context))
                except SchemaError as e:
                    errors.append(e.errors)
                    continue

            if not matched:
                raise PolymorphicError({'__any__': errors})

            if all(isinstance(value, Mapping) for value in matched):
                matched.append(Object(cursor.url))
                return reduce(operator.or_, reversed(matched))

            return matched[0]
        else:
            candidate = self.discriminator.match(self.property_types, cursor)
            assert isinstance(candidate, AbstractType)
            return candidate.unmarshal(cursor, context=context)


class OneOfType(AbstractType):

    """The given data must be valid against exactly one of the given subschemas.

    :param property_types: Types for which the given data must be valid.
    :param discriminator: Discriminator object.
    """

    MESSAGES = {
        'ambiguous': "Ambiguous data"
    }

    __slots__ = [
        'property_types',
        'discriminator'
    ]

    def __init__(self, property_types, discriminator=None, **kwargs):
        self.property_types = property_types
        assert discriminator is None or isinstance(discriminator, Discriminator), (
            "Invalid discriminator object")
        self.discriminator = discriminator
        super(OneOfType, self).__init__(**kwargs)

    def _unmarshal(self, cursor, context):
        if self.discriminator is None:
            matched = []
            errors = []
            for i, candidate in enumerate(self.property_types):
                assert isinstance(candidate, AbstractType)
                try:
                    with cursor.in_scope(i):
                        matched.append(candidate.unmarshal(
                            cursor, context=context))
                except SchemaError as e:
                    errors.append(e.errors)
                    continue

            if not matched:
                raise PolymorphicError({'__one__': errors})
            elif len(matched) > 1:
                raise PolymorphicError(self.messages['ambiguous'])

            return matched[0]
        else:
            candidate = self.discriminator.match(self.property_types, cursor)
            assert isinstance(candidate, AbstractType)
            return candidate.unmarshal(cursor, context=context)


class NotType(AbstractType):

    """Declares that a instance validates if it doesn't validate against the given subschemas.

    :param property_types: Types for which the given data must not be valid.
    """

    MESSAGES = {
        'not_acceptable': "Not acceptable data"
    }

    __slots__ = [
        'property_types'
    ]

    def __init__(self, property_types, **kwargs):
        self.property_types = property_types
        super(NotType, self).__init__(**kwargs)

    def _unmarshal(self, cursor, context):
        for i, property_type in enumerate(self.property_types):
            assert isinstance(property_type, AbstractType)
            try:
                with cursor.in_scope(i):
                    property_type.unmarshal(cursor, context=context)
            except SchemaError:
                pass
            else:
                raise PolymorphicError(self.messages['not_acceptable'])

        return cursor.value


class Schema(object):

    """Schema of object.

    :param name: Schema name.
    :type name: basestring
    :param bases: Base schemas.
    :type bases: tuple | list | `Schema`
    :param properties: Dictionary of property names and corresponding types.
    :type properties: dict
    :param pattern_properties: The correspondence of regular expressions
        with the corresponding types
    :type pattern_properties: tuple | list
    :param additional_properties: Defines additional properties.
        If True then possible any additional properties, that not explicitly describes.
        If False then additional properties not allowed.
        If the property type is specified then additional properties of this type are allowed.
    :type additional_properties: bool | `AbstractType`
    :param validators: Dictionary of validators of properties that depends on others.
    :type validators: dict of callable
    :param defaults: Dictionary of callable objects that provides default values of properties
        that depends on others.
    :type defaults: dict of callable
    """

    __slots__ = [
        'name',
        'properties',
        'additional_properties',
        'pattern_properties',
        'validators',
        'defaults'
    ]

    def __init__(self, name, bases=None,
                 properties=None, pattern_properties=None, additional_properties=None,
                 validators=None, defaults=None):
        self.name = name

        if bases is not None and not isinstance(bases, (tuple, list)):
            bases = (bases, )

        self.properties = OrderedDict()
        self.pattern_properties = None
        self.additional_properties = True
        self.validators = OrderedDict()
        self.defaults = OrderedDict()

        if bases:
            for base in reversed(bases):
                self.properties.update(base.properties)
                if base.pattern_properties is not None:
                    self.pattern_properties = base.pattern_properties
                self.additional_properties = base.additional_properties
                self.validators.update(base.validators)
                self.defaults.update(base.defaults)

        if properties is not None:
            self.properties.update(properties)

        if pattern_properties is not None:
            self.pattern_properties = pattern_properties

        if additional_properties is not None:
            self.additional_properties = additional_properties

        if validators is not None:
            self.validators.update(validators)

        if defaults is not None:
            self.defaults.update(defaults)


class Pass(BaseException):

    """Object for passing value through call stack.

    :param value: Passed value.
    """

    def __init__(self, value):
        self.value = value


class ObjectType(AbstractType):

    """Object property type.

    :param schema: Schema object or callable that returns schema object.
    :param allow_reference: If True then references are allowed. Default: False.
    :param min_properties: Invalidate object when number of properties less than specified.
        Default: None.
    :param max_properties: Invalidate object when number of properties more than specified.
        Default: None.
    """

    MESSAGES = {
        'unmarshal': "Could't interpret value as a object",
        'additional_properties': "Unexpected additional property",
        'min_properties': "Object does not have enough properties",
        'max_properties': "Object has too many properties"
    }

    __slots__ = [
        '_schema',
        'min_properties',
        'max_properties'
    ]

    def __init__(self, schema, min_properties=None, max_properties=None, **kwargs):
        self._schema = schema
        self.min_properties = min_properties
        self.max_properties = max_properties
        super(ObjectType, self).__init__(**kwargs)

    @property
    def schema(self):
        if callable(self._schema):
            self._schema = self._schema()
        return self._schema

    def unmarshal(self, cursor, context=None):
        try:
            return super(ObjectType, self).unmarshal(cursor, context=context)
        except Pass as e:
            return e.value

    def _unmarshalling(self, instance, cursor, context):
        if not cursor.is_mapping:
            raise SchemaError(self.messages['unmarshal'])

        errors = {}

        rogue_props = set(cursor.value) - set(self.schema.properties)
        matched = []
        for rogue_prop in rogue_props:
            if self.schema.pattern_properties is not None:
                for pattern, prop in self.schema.pattern_properties:
                    if pattern.match(str(rogue_prop)):
                        matched.append(rogue_prop)
                        try:
                            with cursor.walk(rogue_prop):
                                instance.pattern_properties[rogue_prop] = prop.unmarshal(
                                    cursor, context=context)
                        except SchemaError as e:
                            errors[rogue_prop] = e.errors

                        break

            if rogue_prop in matched:
                continue

            if self.schema.additional_properties is True:
                with cursor.walk(rogue_prop):
                    instance.additional_properties[rogue_prop] = cursor.value

                matched.append(rogue_prop)

            elif isinstance(self.schema.additional_properties, AbstractType):
                try:
                    with cursor.walk(rogue_prop):
                        instance.additional_properties[rogue_prop] = self.schema.additional_properties.unmarshal(
                            cursor, context=context)
                except SchemaError:
                    continue

                matched.append(rogue_prop)

        rogue_props = rogue_props - set(matched)
        if rogue_props:
            errors.update({
                rogue_prop: self.messages['additional_properties'] for rogue_prop in rogue_props
            })

        for prop_name, prop in iteritems(self.schema.properties):
            try:
                with cursor.walk(prop_name):
                    unmarshalled = prop.unmarshal(cursor, context=context)
            except SchemaError as e:
                errors[prop_name] = e.errors
                continue

            if unmarshalled is Undefined:
                continue

            instance.properties[prop_name] = unmarshalled

        if errors:
            raise UnmarshallingError(errors)

    def _unmarshal(self, cursor, context):
        instance = context.registry.get(cursor.url)

        if instance is not None:
            raise Pass(weakref.proxy(instance))

        instance = Object(cursor.url)
        context.registry[cursor.url] = instance
        self._unmarshalling(instance, cursor, context)
        self._set_defaults(instance, cursor)

        return instance

    def _set_defaults(self, instance, cursor):
        for prop_name, func in iteritems(self.schema.defaults):
            if prop_name not in instance.properties:
                default = func(cursor.value, instance)
                if default is not Undefined:
                    instance.properties[prop_name] = default

    def validate_properties(self, value):
        properties_count = len(value)

        if self.min_properties is not None and properties_count < self.min_properties:
            raise ValidationError(self.messages['min_properties'])

        if self.max_properties is not None and properties_count > self.max_properties:
            raise ValidationError(self.messages['max_properties'])

    def _validate(self, value):
        errors = {}
        for prop_name, validator in iteritems(self.schema.validators):
            try:
                validator(value)
            except ValidationError as e:
                errors.update({prop_name: e.errors})
        if errors:
            raise ValidationError(errors)

        return super(ObjectType, self)._validate(value)


class ObjectOrReferenceType(ObjectType):

    """Object or reference property type. This type allows references
    on objects or another references.

    """

    __slots__ = []

    def _unmarshal(self, cursor, context):
        ref = None
        if cursor.is_ref:
            ref = cursor.value['$ref']

        if ref is not None:
            with cursor.walk_ref(ref):
                return self._unmarshal(cursor, context)

        else:
            return super(ObjectOrReferenceType, self)._unmarshal(cursor, context)
