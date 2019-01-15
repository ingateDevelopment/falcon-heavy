from __future__ import unicode_literals

import os
import copy
import errno

import six
from six import BytesIO

from ..utils import cached_property

from .utils import parse_header_params


class MultiValueDictKeyError(KeyError):
    pass


class MultiValueDict(dict):
    """
    A subclass of dictionary customized to handle multiple values for the
    same key.

    This class exists to solve the irritating problem raised by cgi.parse_qs,
    which returns a list for every key, even though most Web forms submit
    single name-value pairs.
    """
    def __init__(self, mapping=()):
        if isinstance(mapping, MultiValueDict):
            super(MultiValueDict, self).__init__(((k, l[:]) for k, l in mapping.lists()))
        elif isinstance(mapping, dict):
            tmp = {}
            for key, value in six.iteritems(mapping):
                if isinstance(value, (tuple, list)):
                    if len(value) == 0:
                        continue
                    value = list(value)
                else:
                    value = [value]
                tmp[key] = value
            super(MultiValueDict, self).__init__(tmp)
        else:
            tmp = {}
            for key, value in mapping or ():
                tmp.setdefault(key, []).append(value)
            super(MultiValueDict, self).__init__(tmp)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__,
                             super(MultiValueDict, self).__repr__())

    def __getitem__(self, key):
        """
        Returns the last data value for this key, or [] if it's an empty list;
        raises KeyError if not found.
        """
        try:
            list_ = super(MultiValueDict, self).__getitem__(key)
        except KeyError:
            raise MultiValueDictKeyError(repr(key))
        try:
            return list_[-1]
        except IndexError:
            return []

    def __setitem__(self, key, value):
        super(MultiValueDict, self).__setitem__(key, [value])

    def __copy__(self):
        return self.__class__([
            (k, v[:])
            for k, v in self.lists()
        ])

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        result = self.__class__()
        memo[id(self)] = result
        for key, value in dict.items(self):
            dict.__setitem__(
                result, copy.deepcopy(key, memo), copy.deepcopy(value, memo))
        return result

    def __getstate__(self):
        obj_dict = self.__dict__.copy()
        obj_dict['_data'] = {k: self._getlist(k) for k in self}
        return obj_dict

    def __setstate__(self, obj_dict):
        data = obj_dict.pop('_data', {})
        for k, v in data.items():
            self.setlist(k, v)
        self.__dict__.update(obj_dict)

    def get(self, key, default=None):
        """
        Returns the last data value for the passed key. If key doesn't exist
        or value is an empty list, then default is returned.
        """
        try:
            val = self[key]
        except KeyError:
            return default
        if not val:
            return default
        return val

    def _getlist(self, key, default=None, force_list=False):
        """
        Return a list of values for the key.
        Used internally to manipulate values list. If force_list is True,
        return a new copy of values.
        """
        try:
            values = super(MultiValueDict, self).__getitem__(key)
        except KeyError:
            if default is None:
                return []
            return default
        else:
            if force_list:
                values = list(values) if values is not None else None
            return values

    def getlist(self, key, default=None):
        """
        Return the list of values for the key. If key doesn't exist, return a
        default value.
        """
        return self._getlist(key, default, force_list=True)

    def setlist(self, key, list_):
        super(MultiValueDict, self).__setitem__(key, list_)

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
            # Do not return default here because __setitem__() may store
            # another value -- QueryDict.__setitem__() does. Look it up.
        return self[key]

    def setlistdefault(self, key, default_list=None):
        if key not in self:
            if default_list is None:
                default_list = []
            self.setlist(key, default_list)
            # Do not return default_list here because setlist() may store
            # another value -- QueryDict.setlist() does. Look it up.
        return self._getlist(key)

    def appendlist(self, key, value):
        """Appends an item to the internal list associated with key."""
        self.setlistdefault(key).append(value)

    def _iteritems(self):
        """
        Yields (key, value) pairs, where value is the last item in the list
        associated with the key.
        """
        for key in self:
            yield key, self[key]

    def _iterlists(self):
        """Yields (key, list) pairs."""
        return six.iteritems(super(MultiValueDict, self))

    def _itervalues(self):
        """Yield the last value on every key list."""
        for key in self:
            yield self[key]

    if six.PY3:
        items = _iteritems
        lists = _iterlists
        values = _itervalues
    else:
        iteritems = _iteritems
        iterlists = _iterlists
        itervalues = _itervalues

        def items(self):
            return list(self.iteritems())

        def lists(self):
            return list(self.iterlists())

        def values(self):
            return list(self.itervalues())

    def copy(self):
        """Returns a shallow copy of this object."""
        return copy.copy(self)

    def update(self, *args, **kwargs):
        """
        update() extends rather than replaces existing key lists.
        Also accepts keyword args.
        """
        if len(args) > 1:
            raise TypeError("update expected at most 1 arguments, got %d" % len(args))
        if args:
            other_dict = args[0]
            if isinstance(other_dict, MultiValueDict):
                for key, value_list in other_dict.lists():
                    self.setlistdefault(key).extend(value_list)
            else:
                try:
                    for key, value in other_dict.items():
                        self.setlistdefault(key).append(value)
                except TypeError:
                    raise ValueError("MultiValueDict.update() takes either a MultiValueDict or dictionary")
        for key, value in six.iteritems(kwargs):
            self.setlistdefault(key).append(value)

    def dict(self):
        """
        Returns current object as a dict with singular values.
        """
        return {key: self.getlist(key)[0] if len(self.getlist(key)) == 1 else self.getlist(key) for key in self}


class FormStorage(object):

    """Wrapper over multipart form fields."""

    def __init__(self, value=None, content_type=None, headers=None):
        self.value = value

        if headers is None:
            headers = {}

        if content_type is not None:
            headers['content-type'] = content_type

        self.headers = headers

    @cached_property
    def _parsed_content_type(self):
        return parse_header_params(self.content_type)

    @property
    def content_type(self):
        """The content-type sent in the header.  Usually not available"""
        return self.headers.get('content-type', 'text/plain')

    @property
    def mimetype(self):
        """Like :attr:`content_type`, but without parameters (eg, without
        charset, type etc.) and always lowercase.  For example if the content
        type is ``text/HTML; charset=utf-8`` the mimetype would be
        ``'text/html'``.
        """
        return self._parsed_content_type[0].lower()

    @property
    def mimetype_params(self):
        """The mimetype parameters as dict.  For example if the content
        type is ``text/html; charset=utf-8`` the params would be
        ``{'charset': 'utf-8'}``.
        """
        return self._parsed_content_type[1]


_empty_stream = BytesIO()


class FileStorage(object):

    """The :class:`FileStorage` class is a thin wrapper over incoming files.
    It is used by the request object to represent uploaded files.  All the
    attributes of the wrapper stream are proxied by the file storage so
    it's possible to do ``storage.read()`` instead of the long form
    ``storage.stream.read()``.
    """

    def __init__(self, stream=None, filename=None,
                 content_type=None, content_length=None,
                 headers=None):
        self.stream = stream or _empty_stream
        self._filename = filename
        if headers is None:
            headers = {}
        self.headers = headers
        if content_type is not None:
            headers['content-type'] = content_type
        if content_length is not None:
            headers['content-length'] = str(content_length)

    @property
    def filename(self):
        # Sanitize the file name so that it can't be dangerous.
        filename = self._filename
        if filename is not None:
            # Just use the basename of the file -- anything else is dangerous.
            filename = os.path.basename(filename)

            # File names longer than 255 characters can cause problems on older OSes.
            if len(filename) > 255:
                filename, ext = os.path.splitext(filename)
                ext = ext[:255]
                filename = filename[:255 - len(ext)] + ext

        return filename

    @filename.setter
    def filename(self, filename):
        self._filename = filename

    @cached_property
    def _parsed_content_type(self):
        return parse_header_params(self.content_type)

    @property
    def content_type(self):
        """The content-type sent in the header.  Usually not available"""
        return self.headers.get('content-type', 'application/octet-stream')

    @property
    def content_length(self):
        """The content-length sent in the header.  Usually not available"""
        return int(self.headers.get('content-length') or 0)

    @property
    def mimetype(self):
        """Like :attr:`content_type`, but without parameters (eg, without
        charset, type etc.) and always lowercase.  For example if the content
        type is ``text/HTML; charset=utf-8`` the mimetype would be
        ``'text/html'``.
        """
        return self._parsed_content_type[0].lower()

    @property
    def mimetype_params(self):
        """The mimetype parameters as dict.  For example if the content
        type is ``text/html; charset=utf-8`` the params would be
        ``{'charset': 'utf-8'}``.
        """
        return self._parsed_content_type[1]

    def read(self, size=None):
        return self.stream.read(size)

    def save(self, dst, buffer_size=16 * 1024):
        """Save the file to a destination path or file object.  If the
        destination is a file object you have to close it yourself after the
        call.  The buffer size is the number of bytes held in memory during
        the copy process.  It defaults to 16KB.

        For secure file saving also have a look at :func:`secure_filename`.

        :param dst: a filename or open file object the uploaded file
            is saved to.
        :param buffer_size: the size of the buffer.  This works the same as
            the `length` parameter of :func:`shutil.copyfileobj`.
        """
        from shutil import copyfileobj
        close_dst = False
        if isinstance(dst, six.string_types):
            dst = open(dst, 'wb')
            close_dst = True
        try:
            copyfileobj(self.stream, dst, buffer_size)
        finally:
            if close_dst:
                dst.close()

    def close(self):
        """Close the underlying file if possible."""
        try:
            return self.stream.close()
        except OSError as e:
            if e.errno != errno.ENOENT:
                # Means the file was moved or deleted before the tempfile
                # could unlink it.  Still sets self.file.close_called and
                # calls self.file.file.close() before the exception
                raise

    def __nonzero__(self):
        return bool(self.filename)

    __bool__ = __nonzero__

    def __iter__(self):
        return iter(self.stream)

    def __repr__(self):
        return '<%s: %r (%r)>' % (
            self.__class__.__name__,
            self.filename,
            self.content_type
        )
