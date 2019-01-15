from __future__ import unicode_literals

import json

from mimeparse import best_match


class MediaDeserializers(object):

    __slots__ = [
        '_deserializers'
    ]

    def __init__(self):
        self._deserializers = {}

    def add(self, media_range, deserializer):
        self._deserializers[media_range] = deserializer

    def find_by_media_type(self, media_type):
        if media_type in self._deserializers:
            return self._deserializers[media_type]

        best = best_match(self._deserializers.keys(), media_type)
        if best:
            return self._deserializers[best]


def json_deserializer(raw, encoding='utf-8'):
    return json.loads(raw, encoding=encoding)


media_deserializers = MediaDeserializers()

media_deserializers.add('application/json', json_deserializer)
media_deserializers.add('application/json; charset=UTF-8', json_deserializer)
