from __future__ import unicode_literals

from collections import namedtuple


PARAMETER_TYPES = namedtuple(
    'PARAMETER_TYPES',
    ['PRIMITIVE', 'ARRAY', 'OBJECT']
)(
    PRIMITIVE='primitive',
    ARRAY='array',
    OBJECT='object'
)
