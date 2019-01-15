from __future__ import unicode_literals

import weakref

from wrapt import ObjectProxy

from .._compat import Mapping

from ..schema.types import AbstractConvertible
from ..schema.undefined import Undefined
from ..schema.path import Path
from ..schema.exceptions import SchemaError, Error
from ..schema.ref_resolver import RefResolutionError


class RegisteredType(AbstractConvertible):

    """Registered type

    Serves for storing a converted data in the registry

    :param subtype: registered type
    :type subtype: AbstractConvertible
    """

    __slots__ = [
        'subtype'
    ]

    def __init__(self, subtype, **kwargs):
        self.subtype = subtype
        super(RegisteredType, self).__init__(**kwargs)

    def convert(self, raw, path, registry=None, **context):
        if registry is None:
            raise ValueError("Registry should be specified")

        if isinstance(raw, Mapping) and '$ref' in raw:
            return self.subtype.convert(
                raw,
                path,
                registry=registry,
                **context
            )

        else:
            if path in registry:
                return registry[path]

            proxy = ObjectProxy(None)
            registry[path] = proxy
            try:
                converted = self.subtype.convert(
                    raw,
                    path,
                    registry=registry,
                    **context
                )
                proxy.__wrapped__ = weakref.proxy(converted)
                registry[path] = converted

                return converted
            except SchemaError:
                registry[path] = Undefined
                raise


class ReferencedType(AbstractConvertible):

    """Referenced type

    Serves for resolving references and storing converted data in the registry

    :param subtype: referenced type
    :type subtype: AbstractConvertible
    """

    MESSAGES = {
        'bad_reference': "$refs must reference a valid location in the document",
        'unresolvable_recursive_reference': "Unresolvable recursive reference was found",
        'unresolvable_reference': "Couldn't resolve reference"
    }

    __slots__ = [
        'subtype'
    ]

    def __init__(self, subtype, **kwargs):
        self.subtype = subtype
        super(ReferencedType, self).__init__(**kwargs)

    def convert(self, raw, path, visited_refs=None, ref_resolver=None, registry=None, **context):
        if ref_resolver is None:
            raise ValueError("References resolver should be specified")

        if registry is None:
            raise ValueError("Registry should be specified")

        ref = None
        if isinstance(raw, Mapping) and '$ref' in raw:
            ref = raw['$ref']

        visited_refs = visited_refs or set()

        if ref is not None:
            try:
                with ref_resolver.resolving(ref) as target:
                    path = Path(ref_resolver.resolution_scope)

                    if path in visited_refs:
                        raise SchemaError(
                            Error(path, self.messages['unresolvable_recursive_reference']))

                    value = registry.get(path)

                    if value is Undefined:
                        raise SchemaError(
                            Error(path, self.messages['bad_reference']))

                    elif value is not None:
                        return value

                    proxy = ObjectProxy(None)
                    registry[path] = proxy
                    visited_refs.add(path)
                    try:
                        converted = self.convert(
                            target,
                            path,
                            visited_refs=visited_refs,
                            ref_resolver=ref_resolver,
                            registry=registry,
                            **context
                        )
                        proxy.__wrapped__ = weakref.proxy(converted)
                        registry[path] = converted

                        return converted

                    except SchemaError as e:
                        registry[path] = Undefined
                        raise SchemaError(
                            Error(path, self.messages['bad_reference']), *e.errors)

                    finally:
                        visited_refs.discard(path)

            except RefResolutionError:
                raise SchemaError(
                    Error(path, self.messages['unresolvable_reference']))

        else:
            return self.subtype.convert(
                raw,
                path,
                ref_resolver=ref_resolver,
                registry=registry,
                **context
            )
