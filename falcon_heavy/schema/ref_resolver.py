from __future__ import unicode_literals

import yaml
import json
import contextlib

from six.moves.urllib_parse import urljoin, unquote, urldefrag, urlsplit as _urlsplit, urlparse, SplitResult
from six.moves.urllib.request import urlopen

try:
    import requests
except ImportError:
    requests = None

from .._compat import lru_cache, Sequence, MutableMapping


__all__ = (
    'RefResolver',
    'RefResolutionError',
    'URIDict'
)


class RefResolutionError(Exception):
    pass


def urlsplit(url):
    scheme, netloc, path, query, fragment = _urlsplit(url)
    if '#' in path:
        path, fragment = path.split('#', 1)
    return SplitResult(scheme, netloc, path, query, fragment)


class URIDict(MutableMapping):
    """
    Dictionary which uses normalized URIs as keys.

    """

    def normalize(self, uri):
        return urlsplit(uri).geturl()

    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.store.update(*args, **kwargs)

    def __getitem__(self, uri):
        return self.store[self.normalize(uri)]

    def __setitem__(self, uri, value):
        self.store[self.normalize(uri)] = value

    def __delitem__(self, uri):
        del self.store[self.normalize(uri)]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __repr__(self):
        return repr(self.store)


class RefResolver(object):
    """
    Resolve JSON References.

    :param base_uri: URI of the referring document.
    :type base_uri: basestring
    :param referrer: The actual referring document.
    :type referrer: dict
    :param store: A mapping from URIs to documents to cache.
    :type store: dict
    :param cache_remote: Whether remote refs should be cached after
        first resolution.
    :type cache_remote: bool
    :param handlers: A mapping from URI schemes to functions that
        should be used to retrieve them.
    :type handlers: dict
    :param urljoin_cache: A cache that will be used for
        caching the results of joining the resolution scope to subscopes.
    :type urljoin_cache: functools.lru_cache
    :param remote_cache: A cache that will be used for
        caching the results of resolved remote URLs.
    :type remote_cache: functools.lru_cache
    """

    def __init__(
        self,
        base_uri,
        referrer,
        store=(),
        cache_remote=True,
        handlers=(),
        urljoin_cache=None,
        remote_cache=None,
    ):
        if urljoin_cache is None:
            urljoin_cache = lru_cache(1024)(urljoin)
        if remote_cache is None:
            remote_cache = lru_cache(1024)(self.resolve_from_url)

        self.referrer = referrer
        self.cache_remote = cache_remote
        self.handlers = dict(handlers)

        self._scopes_stack = [base_uri]
        self.store = URIDict()
        self.store.update(store)
        self.store[base_uri] = referrer

        self._urljoin_cache = urljoin_cache
        self._remote_cache = remote_cache

    def push_scope(self, scope):
        self._scopes_stack.append(
            self._urljoin_cache(self.resolution_scope, scope),
        )

    def pop_scope(self):
        try:
            self._scopes_stack.pop()
        except IndexError:
            raise RefResolutionError(
                "Failed to pop the scope from an empty stack. "
                "`pop_scope()` should only be called once for every "
                "`push_scope()`",
            )

    @property
    def resolution_scope(self):
        return self._scopes_stack[-1]

    @property
    def base_uri(self):
        uri, _ = urldefrag(self.resolution_scope)
        return uri

    @contextlib.contextmanager
    def in_scope(self, scope):
        self.push_scope(scope)
        try:
            yield
        finally:
            self.pop_scope()

    @contextlib.contextmanager
    def resolving(self, ref):
        """
        Context manager which resolves a JSON ``ref`` and enters the
        resolution scope of this ref.

        :param ref: Reference to resolve.
        :type ref: str
        """

        url, resolved = self.resolve(ref)
        self.push_scope(url)
        try:
            yield resolved
        finally:
            self.pop_scope()

    def resolve(self, ref):
        url = self._urljoin_cache(self.resolution_scope, ref)
        return url, self._remote_cache(url)

    def resolve_from_url(self, url):
        url, fragment = urldefrag(url)
        try:
            document = self.store[url]
        except KeyError:
            try:
                document = self.resolve_remote(url)
            except Exception as exc:
                raise RefResolutionError(exc)

        return self.resolve_fragment(document, fragment)

    def resolve_fragment(self, document, fragment):
        """
        Resolve a ``fragment`` within the referenced ``document``.

        :param document: The referrant document.
        :type document: dict
        :param fragment: A URI fragment to resolve within it
        :type fragment: str
        """

        fragment = fragment.lstrip('/')
        parts = unquote(fragment).split('/') if fragment else []

        for part in parts:
            part = part.replace('~1', '/').replace('~0', '~')

            if isinstance(document, Sequence):
                # Array indexes should be turned into integers
                try:
                    part = int(part)
                except ValueError:
                    pass
            try:
                document = document[part]
            except (TypeError, LookupError):
                raise RefResolutionError(
                    "Unresolvable JSON pointer: %r" % fragment
                )

        return document

    def resolve_remote(self, uri):
        """
        Resolve a remote ``uri``.

        If called directly, does not check the store first, but after
        retrieving the document at the specified URI it will be saved in
        the store if :attr:`cache_remote` is True.

        If the requests_ library is present, ``jsonschema`` will use it to
        request the remote ``uri``, so that the correct encoding is
        detected and used.

        If it isn't, or if the scheme of the ``uri`` is not ``http`` or
        ``https``, UTF-8 is assumed.

        :param uri: The URI to resolve.
        :type uri: str
        :return: The retrieved document
        """

        scheme = urlsplit(uri).scheme

        if scheme in self.handlers:
            result = self.handlers[scheme](uri)

        elif (
            scheme in ['http', 'https'] and
            requests and
            getattr(requests.Response, 'json', None) is not None
        ):
            # Requests has support for detecting the correct encoding of
            # json over http
            if callable(requests.Response.json):
                result = requests.get(uri).json()
            else:
                result = requests.get(uri).json

        elif scheme == 'file':
            path = urlparse(uri, 'file').path

            with open(path) as fh:
                result = yaml.safe_load(fh)

        else:
            # Otherwise, pass off to urllib and assume utf-8
            result = json.loads(urlopen(uri).read().decode('utf-8'))

        if self.cache_remote:
            self.store[uri] = result

        return result
