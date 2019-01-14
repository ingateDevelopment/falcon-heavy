from __future__ import absolute_import

import base64

import six

import wrapt

from werkzeug.datastructures import Headers
from werkzeug.http import parse_options_header


def coalesce(*args):
    """Returns the first not None item.

    :param args: list of items for checking
    :return the first not None item, or None
    """
    try:
        return next((arg for arg in args if arg is not None))
    except StopIteration:
        return None


class FormStorage(six.text_type):

    """Wrapper over multipart form fields."""

    def __new__(cls, value=None, name=None, content_type=None, headers=None):
        klass = six.text_type.__new__(cls, value)

        klass.name = name

        if headers is None:
            headers = Headers()

        if content_type is not None:
            headers['Content-Type'] = content_type

        klass.headers = headers

        return klass

    def _parse_content_type(self):
        if not hasattr(self, '_parsed_content_type'):
            self._parsed_content_type = \
                parse_options_header(self.content_type)

    @property
    def content_type(self):
        """The content-type sent in the header.  Usually not available"""
        return self.headers.get('content-type')

    @property
    def mimetype(self):
        """Like :attr:`content_type`, but without parameters (eg, without
        charset, type etc.) and always lowercase.  For example if the content
        type is ``text/HTML; charset=utf-8`` the mimetype would be
        ``'text/html'``.
        """
        self._parse_content_type()
        return self._parsed_content_type[0].lower()

    @property
    def mimetype_params(self):
        """The mimetype parameters as dict.  For example if the content
        type is ``text/html; charset=utf-8`` the params would be
        ``{'charset': 'utf-8'}``.
        """
        self._parse_content_type()
        return self._parsed_content_type[1]


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
