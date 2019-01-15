from __future__ import unicode_literals

from six import iteritems

from .types import ContentTypeBestMatchedType


class ContentFactory(object):

    def __init__(self, media_type_factory):
        self.media_type_factory = media_type_factory

    def generate(self, content):
        """
        Generates content.

        :param content: Map of content types and media type objects.
        :type content: dict of Object
        :return: Content type.
        :rtype: ContentTypeBestMatchedType
        """
        return ContentTypeBestMatchedType(supported={
            content_type: self.media_type_factory.generate(content_type, media_type)
            for content_type, media_type in iteritems(content)
        })
