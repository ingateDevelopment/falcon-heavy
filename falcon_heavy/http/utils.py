from __future__ import unicode_literals

import re

import six
from six.moves.urllib.parse import unquote

from .exceptions import TooManyFieldsSent


FIELDS_MATCH = re.compile('[&;]')


def limited_parse_qsl(qs, keep_blank_values=False, encoding='utf-8',
                      errors='replace', fields_limit=None):
    """
    Return a list of key/value tuples parsed from query string.
    Copied from urlparse with an additional "fields_limit" argument.
    Copyright (C) 2013 Python Software Foundation (see LICENSE.python).

    :param qs: percent-encoded query string to be parsed
    :param keep_blank_values: flag indicating whether blank values in
        percent-encoded queries should be treated as blank strings. A
        true value indicates that blanks should be retained as blank
        strings. The default false value indicates that blank values
        are to be ignored and treated as if they were  not included
    :param encoding: specify how to decode percent-encoded sequences
        into Unicode characters, as accepted by the bytes.decode() method
    :param errors: may be given to set the desired error handling scheme
    :param fields_limit: maximum number of fields parsed or an exception
        is raised. None means no limit and is the default
    """
    if fields_limit:
        pairs = FIELDS_MATCH.split(qs, fields_limit)
        if len(pairs) > fields_limit:
            raise TooManyFieldsSent("Too many GET/POST parameters")
    else:
        pairs = FIELDS_MATCH.split(qs)
    r = []
    for name_value in pairs:
        if not name_value:
            continue
        nv = name_value.split(str('='), 1)
        if len(nv) != 2:
            # Handle case of a control-name with no equal sign
            if keep_blank_values:
                nv.append('')
            else:
                continue
        if len(nv[1]) or keep_blank_values:
            if six.PY3:
                name = nv[0].replace('+', ' ')
                name = unquote(name, encoding=encoding, errors=errors)
                value = nv[1].replace('+', ' ')
                value = unquote(value, encoding=encoding, errors=errors)
            else:
                name = unquote(nv[0].replace(b'+', b' '))
                value = unquote(nv[1].replace(b'+', b' '))
            r.append((name, value))
    return r


def parse_header(line):
    """
    Parse the header into a name-value.
    """
    parts = line.split(b':', 1)

    if len(parts) == 2:
        return parts[0].lower().strip().decode('ascii'), parts[1].strip()

    else:
        raise ValueError("Invalid header: %r" % line)


def parse_header_params(value):
    """
    Parse header parameters. Returns unicode for key/name, bytes for value which
    will be decoded later.
    """
    parts = _split_header_params(b';' + value)
    mimetype = parts.pop(0).lower().decode('ascii')
    params = {}
    for part in parts:
        i = part.find(b'=')
        if i >= 0:
            has_encoding = False
            name = part[:i].strip().lower().decode('ascii')
            if name.endswith('*'):
                # Lang/encoding embedded in the value (like "filename*=UTF-8''file.ext")
                # http://tools.ietf.org/html/rfc2231#section-4
                name = name[:-1]
                if part.count(b"'") == 2:
                    has_encoding = True
            value = part[i + 1:].strip()
            if has_encoding:
                encoding, lang, value = value.split(b"'")
                if six.PY3:
                    value = unquote(value.decode(), encoding=encoding.decode())
                else:
                    value = unquote(value).decode(encoding)
            if len(value) >= 2 and value[:1] == value[-1:] == b'"':
                value = value[1:-1]
                value = value.replace(b'\\\\', b'\\').replace(b'\\"', b'"')
            params[name] = value
    return mimetype, params


def _split_header_params(s):
    """Split header parameters."""
    result = []
    while s[:1] == b';':
        s = s[1:]
        end = s.find(b';')
        while end > 0 and s.count(b'"', 0, end) % 2:
            end = s.find(b';', end + 1)
        if end < 0:
            end = len(s)
        f = s[:end]
        result.append(f.strip())
        s = s[end:]
    return result
