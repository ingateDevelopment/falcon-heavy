from __future__ import unicode_literals

import falcon


class FalconHeavyHTTPError(Exception):
    """Base Falcon Heavy HTTP error"""

    def __init__(self, status, data=None, content_type=falcon.MEDIA_JSON, headers=None):
        self.status = status
        self.data = data
        self.content_type = content_type
        self.headers = headers

    @staticmethod
    def handle(ex, req, resp, params):
        resp.content_type = ex.content_type
        resp.status = ex.status

        if ex.data is not None:
            resp.media = ex.data

        if ex.headers is not None:
            resp.set_headers(ex.headers)
