from __future__ import unicode_literals

from six import PY3


class Error(object):

    __slots__ = [
        'path',
        'message'
    ]

    def __init__(self, path, message):
        self.path = path
        self.message = message

    def __eq__(self, other):
        if not isinstance(other, Error):
            raise NotImplementedError

        return self.path == other.path and self.message == other.message

    def __hash__(self):
        return hash((self.path, self.message))

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return "Schema error at %s: %s" % (self.path, self.message)

    if PY3:
        __str__ = __unicode__

    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.path, self.message)


class SchemaError(Exception):

    def __init__(self, *errors):
        self.errors = errors

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return "\n".join(map(unicode, self.errors))

    if PY3:
        __str__ = __unicode__

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, ', '.join(map(repr, self.errors)))
