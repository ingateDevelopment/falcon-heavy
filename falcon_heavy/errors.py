from __future__ import absolute_import, unicode_literals

import falcon


class FalconHeavyHTTPError(Exception):

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


class FalconHeavyHTTPBadRequest(FalconHeavyHTTPError):

    def __init__(self, **kwargs):
        super(FalconHeavyHTTPBadRequest, self).__init__(falcon.HTTP_400, **kwargs)


class FalconHeavyInvalidRequest(FalconHeavyHTTPBadRequest):
    pass


class FalconHeavyRequestEntityTooLarge(FalconHeavyHTTPBadRequest):

    def __init__(self, **kwargs):
        super(FalconHeavyHTTPBadRequest, self).__init__(falcon.HTTP_413, **kwargs)


class FalconHeavyHTTPForbidden(FalconHeavyHTTPError):

    def __init__(self, **kwargs):
        super(FalconHeavyHTTPForbidden, self).__init__(falcon.HTTP_403, **kwargs)
