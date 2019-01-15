from __future__ import unicode_literals

from itertools import chain

from six import iteritems

import falcon

from ._compat import Mapping


class FalconHeavyResponse(falcon.Response):

    __slots__ = []

    @property
    def headers(self):
        return self._headers

    def set_header(self, name, value, explode=False):
        if isinstance(value, (tuple, list)):
            value = ','.join(value)
        elif isinstance(value, Mapping):
            if explode:
                value = ','.join('{}={}'.format(k, v) for k, v in iteritems(value))
            else:
                value = ','.join(map(str, chain(*value.items())))

        super(FalconHeavyResponse, self).set_header(name, value)

    def set_headers(self, headers, explode=False):
        if isinstance(headers, dict):
            headers = headers.items()

        for name, value in headers:
            self.set_header(name, value, explode=explode)
