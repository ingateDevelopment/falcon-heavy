from __future__ import absolute_import

import random
import string
import mimetypes
from io import BytesIO

from six import string_types
from six.moves.urllib_parse import urlencode

from werkzeug._compat import to_bytes
from werkzeug.datastructures import FileStorage

from .utils import FormStorage


_BOUNDARY_CHARS = string.digits + string.ascii_letters


def encode_multipart(values, boundary=None, charset='utf-8'):
    """
    Encode values as multipart/form-data.

    """
    if boundary is None:
        boundary = ''.join(random.choice(_BOUNDARY_CHARS) for _ in range(30))

    body = BytesIO()
    write_binary = body.write

    def write(s):
        write_binary(s.encode(charset))

    for value in values:
        if isinstance(value, FormStorage):
            write('--{0}\r\n'.format(boundary))
            write('Content-Disposition: form-data; name="{0}"\r\n'.format(value.name))

            for header in value.headers:
                write('{0}: {1}\r\n'.format(*header))

            write('\r\n')

            if not isinstance(value, string_types):
                value = str(value)

            value = to_bytes(value, charset)
            write_binary(value)

            write('\r\n')

        elif isinstance(value, FileStorage):
            reader = value.stream.read

            write('--{0}\r\n'.format(boundary))
            write('Content-Disposition: form-data; name="{0}"; filename="{1}"\r\n'.format(
                value.name, value.filename))

            content_type = value.content_type
            if content_type is None:
                content_type = (
                    value.filename and mimetypes.guess_type(value.filename)[0] or 'application/octet-stream')

            value.headers.set('Content-Type', content_type)
            for header in value.headers:
                write('{0}: {1}\r\n'.format(*header))

            write('\r\n')

            while 1:
                chunk = reader(16384)
                if not chunk:
                    break

                if isinstance(chunk, string_types):
                    chunk = to_bytes(chunk, charset)

                write_binary(chunk)

            write('\r\n')

    write('--{0}--\r\n'.format(boundary))

    length = body.tell()
    body.seek(0)

    headers = {
        'Content-Type': 'multipart/form-data; boundary={0}'.format(boundary),
        'Content-Length': str(length),
    }

    return body.read(), headers


def encode_urlencoded_form(fields):
    """
    Encode dict of fields as application/x-www-form-urlencoded.

    """
    body = urlencode(fields, doseq=1)
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    return body, headers
