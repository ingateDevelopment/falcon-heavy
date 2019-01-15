from __future__ import unicode_literals

import json
import datetime
import decimal

import six

import rfc3339

from falcon import media

from ..utils import is_flo


class FalconHeavyJsonEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return rfc3339.rfc3339(o)

        elif isinstance(o, datetime.date):
            return o.isoformat()

        elif isinstance(o, decimal.Decimal):
            return str(o)

        elif is_flo(o):
            chunks = []
            while 1:
                chunk = o.read(64 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)

            return ''.join(chunks)

        return json.JSONEncoder.default(self, o)


class FalconHeavyJSONHandler(media.JSONHandler):

    def serialize(self, obj):
        result = json.dumps(obj, cls=FalconHeavyJsonEncoder, ensure_ascii=False)
        if six.PY3 or not isinstance(result, bytes):
            return result.encode('utf-8')

        return result
