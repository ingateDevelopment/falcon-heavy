import json
import inspect
import itertools
import functools

import yaml


def read_yaml_file(path):
    """Open a YAML file, read it and return its contents."""

    with open(path) as fh:
        return yaml.safe_load(fh)


def read_json_file(path):
    """Open a JSON file, read it and return its contents."""

    with open(path) as fn:
        return json.load(fn)


def unbool(element, true=object(), false=object()):
    """A hack to make True and 1 and False and 0 unique for ``uniq``."""

    if element is True:
        return true
    elif element is False:
        return false
    return element


def uniq(container):
    """Check if all of a container's elements are unique.

    Successively tries first to rely that the elements are hashable, then
    falls back on them being sortable, and finally falls back on brute
    force.
    """

    try:
        return len(set(unbool(i) for i in container)) == len(container)
    except TypeError:
        try:
            sort = sorted(unbool(i) for i in container)
            sliced = itertools.islice(sort, 1, None)
            for i, j in zip(sort, sliced):
                if i == j:
                    return False
        except (NotImplementedError, TypeError):
            seen = []
            for e in container:
                e = unbool(e)
                if e in seen:
                    return False
                seen.append(e)
    return True


def prepare_validator(func, args_count):
    if isinstance(func, classmethod):
        func = func.__get__(object).__func__
    if len(inspect.getargspec(func).args) < args_count:
        @functools.wraps(func)
        def newfunc(*args, **kwargs):
            return func(*args, **kwargs)
        return newfunc
    return func


def is_file_like(value):
    """Check if value is file-like object."""
    try:
        value.read(0)
    except (AttributeError, TypeError):
        return False

    return True
