from __future__ import unicode_literals

import re
import datetime
import base64
from decimal import Decimal

import six
from six.moves import html_entities

import wrapt


class FalconHeavyUnicodeDecodeError(UnicodeDecodeError):
    def __init__(self, obj, *args):
        self.obj = obj
        UnicodeDecodeError.__init__(self, *args)

    def __str__(self):
        original = UnicodeDecodeError.__str__(self)
        return '%s. You passed in %r (%s)' % (original, self.obj, type(self.obj))


_PROTECTED_TYPES = six.integer_types + (
    type(None), float, Decimal, datetime.datetime, datetime.date, datetime.time
)


def is_protected_type(obj):
    """Determine if the object instance is of a protected type.
    Objects of protected types are preserved as-is when passed to
    force_text(strings_only=True).
    """
    return isinstance(obj, _PROTECTED_TYPES)


def force_text(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_text, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.
    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first for performance reasons.
    if issubclass(type(s), six.text_type):
        return s
    if strings_only and is_protected_type(s):
        return s
    try:
        if not issubclass(type(s), six.string_types):
            if six.PY3:
                if isinstance(s, bytes):
                    s = six.text_type(s, encoding, errors)
                else:
                    s = six.text_type(s)
            elif hasattr(s, '__unicode__'):
                s = six.text_type(s)
            else:
                s = six.text_type(bytes(s), encoding, errors)
        else:
            # Note: We use .decode() here, instead of six.text_type(s, encoding,
            # errors), so that if s is a SafeBytes, it ends up being a
            # SafeText at the end.
            s = s.decode(encoding, errors)
    except UnicodeDecodeError as e:
        if not isinstance(s, Exception):
            raise FalconHeavyUnicodeDecodeError(s, *e.args)
        else:
            # If we get to here, the caller has passed in an Exception
            # subclass populated with non-ASCII bytestring data without a
            # working unicode method. Try to handle this without raising a
            # further exception by individually forcing the exception args
            # to unicode.
            s = ' '.join(force_text(arg, encoding, strings_only, errors)
                         for arg in s)
    return s


def _replace_entity(match):
    text = match.group(1)
    if text[0] == '#':
        text = text[1:]
        try:
            if text[0] in 'xX':
                c = int(text[1:], 16)
            else:
                c = int(text)
            return six.unichr(c)
        except ValueError:
            return match.group(0)
    else:
        try:
            return six.unichr(html_entities.name2codepoint[text])
        except (ValueError, KeyError):
            return match.group(0)


_entity_re = re.compile(r"&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));")


def unescape_entities(text):
    return _entity_re.sub(_replace_entity, force_text(text))


class Base64EncodableStream(wrapt.ObjectProxy):

    """Stream proxy provides base64 encoding on read."""

    def __init__(self, wrapped, encoding='utf-8'):
        super(Base64EncodableStream, self).__init__(wrapped)
        self._self_encoding = encoding

    def read(self, size=None):
        if size is not None:
            size = (size // 3 + 1) * 3

        data = self.__wrapped__.read(size)

        if not data:
            return data

        if six.PY3 and isinstance(data, six.string_types):
            data = data.encode(self._self_encoding, 'strict')

        data = base64.b64encode(data)

        if six.PY3:
            return data.decode('ascii')

        return data


class Base64DecodableStream(wrapt.ObjectProxy):

    """Stream proxy provides base64 decoding on read."""

    def read(self, size=None):
        if size is not None:
            size = (size // 4 + 1) * 4

        data = self.__wrapped__.read(size)

        if not data:
            return data

        if six.PY3 and isinstance(data, six.string_types):
            data = data.encode('ascii')

        return base64.b64decode(data)


class CachedProperty(object):
    """
    Decorator that converts a method with a single self argument into a
    property cached on the instance.
    Optional ``name`` argument allows you to make cached properties of other
    methods. (e.g.  url = cached_property(get_absolute_url, name='url') )
    """
    def __init__(self, func, name=None):
        self.func = func
        self.__doc__ = getattr(func, '__doc__')
        self.name = name or func.__name__

    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        res = instance.__dict__[self.name] = self.func(instance)
        return res


cached_property = CachedProperty


def coalesce(*args):
    """Returns the first not None item.

    :param args: list of items for checking
    :return the first not None item, or None
    """
    try:
        return next((arg for arg in args if arg is not None))
    except StopIteration:
        return None


def is_flo(value):
    """Check if value is file-like object."""
    try:
        value.read(0)
    except (AttributeError, TypeError):
        return False

    return True
