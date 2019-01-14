import json


class SchemaError(Exception):

    def __init__(self, errors):
        if not isinstance(errors, (list, dict)):
            errors = [errors]
        self.errors = errors

    def __str__(self):
        return json.dumps(self.errors)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self.errors))


class CursorError(SchemaError):
    pass


class WalkingError(CursorError):
    pass


class RefResolutionError(CursorError):
    pass


class UnresolvableRecursiveReference(RefResolutionError):
    pass


class UnmarshallingError(SchemaError):
    pass


class DiscriminatorError(UnmarshallingError):
    pass


class ValidationError(SchemaError):
    pass


class PolymorphicError(SchemaError):
    pass
