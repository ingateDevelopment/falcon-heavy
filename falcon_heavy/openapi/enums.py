from __future__ import unicode_literals

from collections import namedtuple


PARAMETER_LOCATIONS = namedtuple(
    'PARAMETER_LOCATIONS',
    ['PATH', 'QUERY', 'HEADER', 'COOKIE']
)(
    PATH='path',
    QUERY='query',
    HEADER='header',
    COOKIE='cookie'
)


PARAMETER_STYLES = namedtuple(
    'PARAMETER_STYLES',
    ['MATRIX', 'LABEL', 'FORM', 'SIMPLE', 'SPACE_DELIMITED', 'PIPE_DELIMITED', 'DEEP_OBJECT']
)(
    MATRIX='matrix',
    LABEL='label',
    FORM='form',
    SIMPLE='simple',
    SPACE_DELIMITED='spaceDelimited',
    PIPE_DELIMITED='pipeDelimited',
    DEEP_OBJECT='deepObject'
)


SCHEMA_TYPES = namedtuple(
    'SCHEMA_TYPES',
    ['INTEGER', 'NUMBER', 'STRING', 'BOOLEAN', 'ARRAY', 'OBJECT']
)(
    INTEGER='integer',
    NUMBER='number',
    STRING='string',
    BOOLEAN='boolean',
    ARRAY='array',
    OBJECT='object'
)


SCHEMA_FORMATS = namedtuple(
    'SCHEMA_FORMATS',
    ['INT32', 'INT64', 'FLOAT', 'DOUBLE', 'BYTE', 'BINARY', 'DATE', 'DATETIME', 'PASSWORD', 'UUID']
)(
    INT32='int32',
    INT64='int64',
    FLOAT='float',
    DOUBLE='double',
    BYTE='byte',
    BINARY='binary',
    DATE='date',
    DATETIME='date-time',
    PASSWORD='password',
    UUID='uuid'
)


SECURITY_SCHEME_TYPES = namedtuple(
    'SECURITY_SCHEME_TYPES',
    ["API_KEY", "HTTP", "OAUTH2", "OPEN_ID_CONNECT"]
)(
    API_KEY='apiKey',
    HTTP='http',
    OAUTH2='oauth2',
    OPEN_ID_CONNECT='openIdConnect'
)


HTTP_SCHEMAS = namedtuple(
    'HTTP_SCHEMAS',
    ['HTTP', 'HTTPS']
)(
    HTTP='http',
    HTTPS='https'
)

HTTP_METHODS = namedtuple(
    'HTTP_METHODS',
    ['GET', 'PUT', 'POST', 'DELETE', 'OPTIONS', 'HEAD', 'PATCH', 'TRACE']
)(
    GET='get',
    PUT='put',
    POST='post',
    DELETE='delete',
    OPTIONS='options',
    HEAD='head',
    PATCH='patch',
    TRACE='trace'
)
