from __future__ import unicode_literals


class SuspiciousOperation(Exception):
    """The user did something suspicious"""


class SuspiciousMultipartForm(SuspiciousOperation):
    """Suspect MIME request in multipart form data"""
    pass


class RequestDataTooBig(SuspiciousOperation):
    """
    The size of the request (excluding any file uploads) exceeded
    specified value.
    """
    pass


class TooManyFieldsSent(SuspiciousOperation):
    """
    The number of fields in a GET or POST request exceeded
    specified value.
    """
    pass
