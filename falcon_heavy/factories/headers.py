from __future__ import unicode_literals

from six import iteritems

from ..openapi.enums import PARAMETER_LOCATIONS

from .parameters import ParametersType


class HeadersFactory(object):

    """Headers factory

    :param parameter_factory: parameter factory
    :type parameter_factory: ParameterFactory
    """

    def __init__(self, parameter_factory):
        self.parameter_factory = parameter_factory

    def generate(self, headers):
        """Generates headers

        :param headers: map of a header name to its definition. "Content-Type" header shall be ignored
        :type headers: dict of ParameterObjectProxy
        :return: headers type
        :rtype: ObjectType
        """
        headers = {name.lower(): header for name, header in iteritems(headers)}
        return ParametersType(
            parameters=[
                self.parameter_factory.generate(PARAMETER_LOCATIONS.HEADER, name, header)
                for name, header in iteritems(headers)
                if name != 'content-type'
            ]
        )
