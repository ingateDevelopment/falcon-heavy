from __future__ import unicode_literals

import re

from six import iterkeys

from .base import BaseOpenApiObjectType
from .types import ReferencedType
from .response import ResponseObjectType


OK_RESPONSE_CODE_PATTERN = re.compile(r'^2(\d{2}|XX)$')


class ResponsesObjectType(BaseOpenApiObjectType):

    __slots__ = []

    MESSAGES = {
        'extra_properties':
            "Should contains HTTP status codes or `default`."
            " The following invalid definitions were found: {0}",
        'has_not_response_codes': "Responses must contains at least one response code",
        'has_not_successful_response': "Responses should contains response for the successful operation call"
    }

    PATTERN_PROPERTIES = {
        re.compile(r'^[1-5](\d{2}|XX)$'): ReferencedType(ResponseObjectType())
    }

    PROPERTIES = {
        'default': ReferencedType(ResponseObjectType())
    }

    def validate_response_codes(self, converted, raw):
        if all(k.startswith('x-') for k in iterkeys(converted.pattern_properties)):
            return self.messages['has_not_response_codes']

        if not any(OK_RESPONSE_CODE_PATTERN.match(k) for k in iterkeys(converted.pattern_properties)):
            return self.messages['has_not_successful_response']
