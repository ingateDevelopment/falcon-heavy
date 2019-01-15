from __future__ import unicode_literals

import importlib

from . import logger


class AbstractResourceResolver(object):

    def resolve(self, resource_id):
        raise NotImplementedError


class RuntimeResourceResolver(AbstractResourceResolver):

    def __init__(self, package):
        self.package = package

    def resolve(self, resource_id):
        parts = resource_id.split(':')

        if len(parts) != 2:
            logger.error(
                "Resource '{}' is not resolved. Invalid resource identifier.".format(resource_id))
            return None

        module_name, attr_path = parts
        module_name = '{}.{}'.format(self.package, module_name)

        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            logger.error(
                "Resource '{}' is not resolved. Couldn't import module '{}': {}".format(
                    resource_id, module_name, e.message))
            return None

        attr = module
        for path_item in attr_path.split('.'):
            try:
                attr = getattr(attr, path_item)
            except AttributeError as e:
                logger.error(
                    "Resource '{}' is not resolved. Couldn't find attribute '{}': {}".format(
                        resource_id, attr_path, e.message))
                return None

        return attr
