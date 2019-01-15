from __future__ import absolute_import

import random
import string
import mimetypes
from io import BytesIO

import six
from six import string_types
from six.moves.urllib_parse import urlencode

from falcon.testing import SimpleTestResource, TestClient

from .resource_resolver import AbstractResourceResolver
from .api import FalconHeavyApi
from http.datastructures import MultiValueDict, FormStorage, FileStorage

from ._compat import to_bytes


class ResourceProxy(object):

    def __init__(self, wrapped):
        self.wrapped = wrapped

    def on_get(self, req, resp, **kwargs):
        return self.wrapped.on_get(req, resp, **kwargs)

    def on_post(self, req, resp, **kwargs):
        return self.wrapped.on_post(req, resp, **kwargs)


class SimpleTestResourceResolver(AbstractResourceResolver):

    def __init__(self, resource=None):
        self.resource = resource or SimpleTestResource()

    def resolve(self, resource_id):
        return lambda: ResourceProxy(self.resource)


def create_client(specification_path, handlers=None):
    res = SimpleTestResource()

    resource_resolver = SimpleTestResourceResolver(res)

    app = FalconHeavyApi(specification_path, resource_resolver)
    app.add_route('/', res)

    if handlers:
        app.req_options.media_handlers.update(handlers)

    client = TestClient(app)
    client.resource = res

    return client


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

    if not isinstance(values, MultiValueDict):
        values = MultiValueDict(values)

    for key, values in values.lists():
        for value in values:
            write('--{0}\r\nContent-Disposition: form-data; name="{1}"'.format(boundary, key))

            if isinstance(value, FormStorage):
                write('\r\n')

                headers = value.headers.copy()

                content_type = value.content_type
                if content_type is not None:
                    headers['Content-Type'] = content_type

                for header in six.iteritems(value.headers):
                    write('{0}: {1}\r\n'.format(*header))

                write('\r\n')

                value = value.value
                if not isinstance(value, string_types):
                    value = str(value)

                value = to_bytes(value, charset)
                write_binary(value)

            elif isinstance(value, FileStorage):
                filename = value.filename

                content_type = value.content_type
                if content_type is None:
                    content_type = (
                        filename and mimetypes.guess_type(filename)[0] or 'application/octet-stream')

                if filename is not None:
                    write('; filename="%s"\r\n' % filename)
                else:
                    write('\r\n')

                headers = value.headers.copy()
                headers['Content-Type'] = content_type

                for header in six.iteritems(value.headers):
                    write('{0}: {1}\r\n'.format(*header))

                write('\r\n')

                while True:
                    chunk = value.read(16 * 1024)
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


def encode_urlencoded_form(values):
    """
    Encode values as application/x-www-form-urlencoded.

    """
    if not isinstance(values, MultiValueDict):
        values = MultiValueDict(values)

    body = urlencode(values.lists(), doseq=1)
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    return body, headers
