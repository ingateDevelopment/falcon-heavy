from __future__ import unicode_literals

import falcon
from falcon import errors

from .http.multipart_parser import MultiPartParser, MultiPartParserError
from .http.datastructures import MultiValueDict
from .http.utils import limited_parse_qsl


class FalconHeavyRequestOptions(falcon.RequestOptions):

    __slots__ = [
        'data_upload_max_number_fields',
        'data_upload_max_memory_size',
        'file_upload_max_memory_size',
        'file_upload_temp_dir',
        'encoding'
    ]

    def __init__(self):
        super(FalconHeavyRequestOptions, self).__init__()
        #: Maximum number of GET/POST parameters that will be read before a
        # SuspiciousOperation (TooManyFieldsSent) is raised.
        self.data_upload_max_number_fields = 1000
        #: The maximum number of bytes to be accepted for in-memory stored form data.
        self.data_upload_max_memory_size = 2621440
        #: Maximum size in bytes of request data (excluding file uploads) that will be
        # read before a SuspiciousOperation (RequestDataTooBig) is raised.
        self.file_upload_max_memory_size = 2621440
        #: Directory in which upload streamed files will be temporarily saved.
        # If `None` then used the operating system's default temporary directory
        # (i.e. "/tmp" on *nix systems).
        self.file_upload_temp_dir = None
        #: Encoding that used in request and response parameters.
        self.encoding = 'utf-8'


class FalconHeavyRequest(falcon.Request):

    __slots__ = []

    @property
    def media(self):
        if self._media is not None:
            return self._media

        if self.method in ('POST', 'PUT', 'PATCH') and self.content_type:
            if self.content_type.startswith('multipart/form-data'):
                try:
                    parser = MultiPartParser(
                        self.bounded_stream,
                        self.content_type,
                        self.content_length,
                        data_upload_max_number_fields=self.options.data_upload_max_number_fields,
                        data_upload_max_memory_size=self.options.data_upload_max_memory_size,
                        file_upload_max_memory_size=self.options.file_upload_max_memory_size,
                        file_upload_temp_dir=self.options.file_upload_temp_dir,
                        encoding=self.options.encoding
                    )
                    form, files = parser.parse()
                except MultiPartParserError:
                    raise errors.HTTPRequestEntityTooLarge()

                self._media = form.dict()
                self._media.update(files.dict())

                return self._media

            if self.content_type.startswith('application/x-www-form-urlencoded') or \
                    self.content_type.startswith('application/x-url-encoded'):
                form = MultiValueDict(limited_parse_qsl(
                    self.bounded_stream.read(),
                    keep_blank_values=self.options.keep_blank_qs_values,
                    encoding=self.options.encoding,
                    fields_limit=self.options.data_upload_max_number_fields
                ))

                self._media = form.dict()

                return self._media

        return super(FalconHeavyRequest, self).media
