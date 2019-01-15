from __future__ import unicode_literals

import re

from six import iteritems

from ..openapi.enums import PARAMETER_LOCATIONS, PARAMETER_STYLES

from ..schema.undefined import Undefined

from .utils import list_to_dict
from .enums import PARAMETER_TYPES


class AbstractExtractable(object):

    def extract(self, params, name, default=Undefined):
        raise NotImplementedError


class AbstractDeserializable(object):

    def deserialize(self, raw):
        raise NotImplementedError


class AbstractParameterStyle(AbstractExtractable, AbstractDeserializable):

    __slots__ = [
        'explode'
    ]

    def __init__(self, explode=False):
        self.explode = explode


class PathPrimitiveParameterSimpleStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        return raw


class PathPrimitiveParameterLabelStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        return raw[1:]


class PathPrimitiveParameterMatrixStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        return raw.split('=', 1)[1]


class PathArrayParameterSimpleStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        return raw.split(',')


class PathArrayParameterLabelStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        if not self.explode:
            return raw[1:].split(',')
        else:
            return raw[1:].split('.')


class PathArrayParameterMatrixStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        if not self.explode:
            return raw.split('=', 1)[1].split(',')
        else:
            return map(lambda x: x.split('=', 1)[1], raw[1:].split(';'))


class PathObjectParameterSimpleStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        if not self.explode:
            return list_to_dict(raw.split(','))
        else:
            return list_to_dict(raw.replace('=', ',').split(','))


class PathObjectParameterLabelStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        if not self.explode:
            return list_to_dict(raw[1:].split(','))
        else:
            return list_to_dict(raw[1:].replace('=', '.').split('.'))


class PathObjectParameterMatrixStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        if not self.explode:
            return list_to_dict(raw.split('=', 1)[1].split(','))
        else:
            return list_to_dict(raw[1:].replace('=', ';').split(';'))


class QueryPrimitiveParameterFormStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        return raw


class QueryArrayParameterFormStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        if self.explode:
            return raw
        else:
            return raw.split(',')


class QueryArrayParameterSpaceDelimitedStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        if self.explode:
            return raw
        else:
            return raw.split(' ')


class QueryArrayParameterPipeDelimitedStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        if self.explode:
            return raw
        else:
            return raw.split('|')


class QueryObjectParameterFormStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        if self.explode:
            return params
        else:
            return params.get(name, default)

    def deserialize(self, raw):
        if self.explode:
            return raw
        else:
            return list_to_dict(raw.split(','))


class QueryObjectParameterDeepObjectStyle(AbstractParameterStyle):

    BRACKETS_PATTERN = re.compile(r'\[[^[\]]*]')

    def extract(self, params, name, default=Undefined):
        params = {k: v for k, v in iteritems(params) if k.startswith('{}['.format(name))}
        if not params:
            return default

        result = {}
        for k, v in iteritems(params):
            if re.sub(self.BRACKETS_PATTERN, '', k) != name:
                raise ValueError("Invalid brackets composition")

            segments = [segment[1:-1] for segment in re.findall(self.BRACKETS_PATTERN, k)]
            it = result
            for segment in segments[:-1]:
                if segment in it:
                    it = it[segment]
                else:
                    it[segment] = it = {}

                if not isinstance(it, dict):
                    raise ValueError("Invalid nested path")

            it[segments[-1]] = v

        return result

    def deserialize(self, raw):
        return raw


class HeaderPrimitiveParameterSimpleStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        return raw


class HeaderArrayParameterSimpleStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        return raw.split(',')


class HeaderObjectParameterSimpleStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        if not self.explode:
            return list_to_dict(raw.split(','))
        else:
            return list_to_dict(raw.replace('=', ',').split(','))


class CookiePrimitiveParameterFormStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        return raw


class CookieArrayParameterFormStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        return raw.split(',')


class CookieObjectParameterFormStyle(AbstractParameterStyle):

    def extract(self, params, name, default=Undefined):
        return params.get(name, default)

    def deserialize(self, raw):
        return list_to_dict(raw.split(','))


PARAMETER_STYLE_CLASSES = {
    (PARAMETER_LOCATIONS.PATH, PARAMETER_TYPES.PRIMITIVE, PARAMETER_STYLES.SIMPLE):
        PathPrimitiveParameterSimpleStyle,
    (PARAMETER_LOCATIONS.PATH, PARAMETER_TYPES.PRIMITIVE, PARAMETER_STYLES.LABEL):
        PathPrimitiveParameterLabelStyle,
    (PARAMETER_LOCATIONS.PATH, PARAMETER_TYPES.PRIMITIVE, PARAMETER_STYLES.MATRIX):
        PathPrimitiveParameterMatrixStyle,
    (PARAMETER_LOCATIONS.PATH, PARAMETER_TYPES.ARRAY, PARAMETER_STYLES.SIMPLE):
        PathArrayParameterSimpleStyle,
    (PARAMETER_LOCATIONS.PATH, PARAMETER_TYPES.ARRAY, PARAMETER_STYLES.LABEL):
        PathArrayParameterLabelStyle,
    (PARAMETER_LOCATIONS.PATH, PARAMETER_TYPES.ARRAY, PARAMETER_STYLES.MATRIX):
        PathArrayParameterMatrixStyle,
    (PARAMETER_LOCATIONS.PATH, PARAMETER_TYPES.OBJECT, PARAMETER_STYLES.SIMPLE):
        PathObjectParameterSimpleStyle,
    (PARAMETER_LOCATIONS.PATH, PARAMETER_TYPES.OBJECT, PARAMETER_STYLES.LABEL):
        PathObjectParameterLabelStyle,
    (PARAMETER_LOCATIONS.PATH, PARAMETER_TYPES.OBJECT, PARAMETER_STYLES.MATRIX):
        PathObjectParameterMatrixStyle,
    (PARAMETER_LOCATIONS.QUERY, PARAMETER_TYPES.PRIMITIVE, PARAMETER_STYLES.FORM):
        QueryPrimitiveParameterFormStyle,
    (PARAMETER_LOCATIONS.QUERY, PARAMETER_TYPES.ARRAY, PARAMETER_STYLES.FORM):
        QueryArrayParameterFormStyle,
    (PARAMETER_LOCATIONS.QUERY, PARAMETER_TYPES.ARRAY, PARAMETER_STYLES.SPACE_DELIMITED):
        QueryArrayParameterSpaceDelimitedStyle,
    (PARAMETER_LOCATIONS.QUERY, PARAMETER_TYPES.ARRAY, PARAMETER_STYLES.PIPE_DELIMITED):
        QueryArrayParameterPipeDelimitedStyle,
    (PARAMETER_LOCATIONS.QUERY, PARAMETER_TYPES.OBJECT, PARAMETER_STYLES.FORM):
        QueryObjectParameterFormStyle,
    (PARAMETER_LOCATIONS.QUERY, PARAMETER_TYPES.OBJECT, PARAMETER_STYLES.DEEP_OBJECT):
        QueryObjectParameterDeepObjectStyle,
    (PARAMETER_LOCATIONS.HEADER, PARAMETER_TYPES.PRIMITIVE, PARAMETER_STYLES.SIMPLE):
        HeaderPrimitiveParameterSimpleStyle,
    (PARAMETER_LOCATIONS.HEADER, PARAMETER_TYPES.ARRAY, PARAMETER_STYLES.SIMPLE):
        HeaderArrayParameterSimpleStyle,
    (PARAMETER_LOCATIONS.HEADER, PARAMETER_TYPES.OBJECT, PARAMETER_STYLES.SIMPLE):
        HeaderObjectParameterSimpleStyle,
    (PARAMETER_LOCATIONS.COOKIE, PARAMETER_TYPES.PRIMITIVE, PARAMETER_STYLES.FORM):
        CookiePrimitiveParameterFormStyle,
    (PARAMETER_LOCATIONS.COOKIE, PARAMETER_TYPES.ARRAY, PARAMETER_STYLES.FORM):
        CookieArrayParameterFormStyle,
    (PARAMETER_LOCATIONS.COOKIE, PARAMETER_TYPES.OBJECT, PARAMETER_STYLES.FORM):
        CookieObjectParameterFormStyle
}
