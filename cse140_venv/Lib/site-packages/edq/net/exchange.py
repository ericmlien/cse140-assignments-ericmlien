import copy
import http
import os
import pathlib
import typing
import urllib.parse

import requests

import edq.net.settings
import edq.net.util
import edq.util.dirent
import edq.util.encoding
import edq.util.hash
import edq.util.json
import edq.util.parse
import edq.util.pyimport
import edq.util.serial

DEFAULT_HTTP_EXCHANGE_EXTENSION: str= '.httpex.json'

QUERY_CLIP_LENGTH: int = 100
""" If the filename of an HTTPExhange being saved is longer than this, then clip it. """

ALLOWED_METHODS: typing.List[str] = [
    'DELETE',
    'GET',
    'HEAD',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
""" Allowed HTTP methods for an HTTPExchange. """

class FileInfo(edq.util.serial.DictConverter):
    """ Store info about files used in HTTP exchanges. """

    def __init__(self,
            path: typing.Union[str, None] = None,
            name: typing.Union[str, None] = None,
            content: typing.Union[str, bytes, None] = None,
            b64_encoded: bool = False,
            **kwargs: typing.Any) -> None:
        # Normalize the path from POSIX-style to the system's style.
        if (path is not None):
            path = str(pathlib.PurePath(pathlib.PurePosixPath(path)))

        self.path: typing.Union[str, None] = path
        """ The on-disk path to a file. """

        if ((name is None) and (self.path is not None)):
            name = os.path.basename(self.path)

        if (name is None):
            raise ValueError("No name was provided for file.")

        self.name: str = name
        """ The name for this file used in an HTTP request. """

        self.content: typing.Union[str, bytes, None] = content
        """ The contents of this file. """

        self.b64_encoded: bool = b64_encoded
        """ Whether the content is a string encoded in Base64. """

        if ((self.path is None) and (self.content is None)):
            raise ValueError("File must have either path or content specified.")

    def resolve_path(self, base_dir: str, load_file: bool = True) -> None:
        """ Resolve this path relative to the given base dir. """

        if ((self.path is not None) and (not os.path.isabs(self.path))):
            self.path = os.path.abspath(os.path.join(base_dir, self.path))

        if ((self.path is not None) and (self.content is None) and load_file):
            self.content = edq.util.dirent.read_file_bytes(self.path)

    def hash_content(self) -> str:
        """
        Compute a hash for the content present.
        If no content is provided, use the path.
        """

        hash_content = self.content

        if (self.b64_encoded and isinstance(hash_content, str)):
            hash_content = edq.util.encoding.from_base64(hash_content)

        if (hash_content is None):
            hash_content = self.path

        return edq.util.hash.sha256_hex(hash_content)

    def to_dict(self,
            context: typing.Union[edq.util.serial.SerializationContext, None] = None,
            ) -> typing.Dict[str, typing.Any]:
        data = vars(self).copy()

        # JSON does not support raw bytes, so we will need to base64 encode any binary content.
        if (isinstance(self.content, bytes)):
            data['content'] = edq.util.encoding.to_base64(self.content)
            data['b64_encoded'] = True

        return data

    @classmethod
    def from_dict(cls,
            data: typing.Dict[str, typing.Any],
            context: typing.Union[edq.util.serial.SerializationContext, None] = None,
            ) -> typing.Any:
        return FileInfo(**data)

class HTTPExchange(edq.util.serial.DictConverter):
    """
    The request and response making up a full HTTP exchange.
    """

    def __init__(self,
            method: str = 'GET',
            url: typing.Union[str, None] = None,
            url_path: typing.Union[str, None] = None,
            url_anchor: typing.Union[str, None] = None,
            parameters: typing.Union[typing.Dict[str, typing.Any], None] = None,
            files: typing.Union[typing.List[typing.Union[FileInfo, typing.Dict[str, typing.Any]]], None] = None,
            headers: typing.Union[typing.Dict[str, typing.Any], None] = None,
            allow_redirects: typing.Union[bool, None] = None,
            response_code: int = http.HTTPStatus.OK,
            response_headers: typing.Union[typing.Dict[str, typing.Any], None] = None,
            json_body: typing.Union[bool, None] = None,
            response_body: typing.Union[str, dict, list, None] = None,
            source_path: typing.Union[str, None] = None,
            response_modifier: typing.Union[str, None] = None,
            finalize: typing.Union[str, None] = None,
            extra_options: typing.Union[typing.Dict[str, typing.Any], None] = None,
            **kwargs: typing.Any) -> None:
        method = str(method).upper()
        if (method not in ALLOWED_METHODS):
            raise ValueError(f"Got unknown/disallowed method: '{method}'.")

        self.method: str = method
        """ The HTTP method for this exchange. """

        url_path, url_anchor, parameters = self._parse_url_components(url, url_path, url_anchor, parameters)

        self.url_path: str = url_path
        """
        The path portion of the request URL.
        Only the path (not domain, port, params, anchor, etc) should be included.
        """

        self.url_anchor: typing.Union[str, None] = url_anchor
        """
        The anchor portion of the request URL (if it exists).
        """

        self.parameters: typing.Dict[str, typing.Any] = parameters
        """
        The parameters/arguments for this request.
        Parameters should be provided here and not encoded into URLs,
        regardless of the request method.
        With the exception of files, all parameters should be placed here.
        """

        if (files is None):
            files = []

        parsed_files = []
        for file in files:
            if (isinstance(file, FileInfo)):
                parsed_files.append(file)
            else:
                parsed_files.append(FileInfo(**file))

        self.files: typing.List[FileInfo] = parsed_files
        """
        A list of files to include in the request.
        The files are represented as dicts with a
        "path" (path to the file on disk) and "name" (the filename to send in the request) field.
        These paths must be POSIX-style paths,
        they will be converted to system-specific paths.
        Once this exchange is ready for use, these paths should be resolved (and probably absolute).
        However, when serialized these paths should probably be relative.
        To reconcile this, resolve_paths() should be called before using this exchange.
        """

        if (headers is None):
            headers = {}

        self.headers: typing.Dict[str, typing.Any] = {key.lower().strip(): value for (key, value) in headers.items()}
        """
        Headers in the request.
        All header keys are stored as lower case.
        """

        if (allow_redirects is None):
            allow_redirects = True

        self.allow_redirects: bool = allow_redirects
        """ Follow redirects. """

        self.response_code: int = response_code
        """ The HTTP status code of the response. """

        if (response_headers is None):
            response_headers = {}

        self.response_headers: typing.Dict[str, typing.Any] = {key.lower().strip(): value for (key, value) in response_headers.items()}
        """
        Headers in the response.
        All header keys are stored as lower case.
        """

        if (json_body is None):
            json_body = isinstance(response_body, (dict, list))

        self.json_body: bool = json_body
        """
        Indicates that the response is JSON and should be converted to/from a string.
        If the response body is passed in a dict/list and this is passed as None,
        then this will be set as true.
        """

        if (self.json_body and isinstance(response_body, (dict, list))):
            response_body = edq.util.json.dumps(response_body)

        self.response_body: typing.Union[str, None] = response_body  # type: ignore[assignment]
        """
        The response that should be sent in this exchange.
        """

        self.response_modifier: typing.Union[str, None] = response_modifier
        """
        This function reference will be used to modify responses (in HTTPExchange.make_request() and HTTPExchange.from_response())
        before sent back to the caller.
        This reference must be importable via edq.util.pyimport.fetch().
        """

        self.finalize: typing.Union[str, None] = finalize
        """
        This function reference will be used to finalize echanges when created using from_response() before sent back to the caller.
        This reference must be importable via edq.util.pyimport.fetch().
        """

        self.source_path: typing.Union[str, None] = source_path
        """
        The path that this exchange was loaded from (if it was loaded from a file).
        This value should never be seriald, but can be useful for testing.
        """

        if (extra_options is None):
            extra_options = {}

        self.extra_options: typing.Dict[str, typing.Any] = extra_options.copy()
        """
        Additional options for this exchange.
        This library will not use these options, but other's may.
        kwargs will also be added to this.
        """

        self.extra_options.update(kwargs)

    def _parse_url_components(self,
            url: typing.Union[str, None] = None,
            url_path: typing.Union[str, None] = None,
            url_anchor: typing.Union[str, None] = None,
            parameters: typing.Union[typing.Dict[str, typing.Any], None] = None,
            ) -> typing.Tuple[str, typing.Union[str, None], typing.Dict[str, typing.Any]]:
        """
        Parse out all URL-based components from raw inputs.
        The URL's path and anchor can either be supplied separately, or as part of the full given URL.
        If content is present in both places, they much match (or an error will be raised).
        Query parameters may be provided in the full URL,
        but will be overwritten by any that are provided separately.
        Any information from the URL aside from the path, anchor/fragment, and query will be ignored.
        Note that path parameters (not query parameters) will be ignored.
        The final url path, url anchor, and parameters will be returned.
        """

        # Do base initialization and cleanup.

        if (url_path is not None):
            url_path = url_path.strip()
            if (url_path == ''):
                url_path = ''
            else:
                url_path = url_path.lstrip('/')

        if (url_anchor is not None):
            url_anchor = url_anchor.strip()
            if (url_anchor == ''):
                url_anchor = None
            else:
                url_anchor = url_anchor.lstrip('#')

        if (parameters is None):
            parameters = {}

        # Parse the URL (if present).

        if ((url is not None) and (url.strip() != '')):
            parts = urllib.parse.urlparse(url)

            # Handle the path.

            path = parts.path.lstrip('/')

            if ((url_path is not None) and (url_path != path)):
                raise ValueError(f"Mismatched URL paths where supplied implicitly ('{path}') and explicitly ('{url_path}').")

            url_path = path

            # Check the optional anchor/fragment.

            if (parts.fragment != ''):
                fragment = parts.fragment.lstrip('#')

                if ((url_anchor is not None) and (url_anchor != fragment)):
                    raise ValueError(f"Mismatched URL anchors where supplied implicitly ('{fragment}') and explicitly ('{url_anchor}').")

                url_anchor = fragment

            # Check for any parameters.

            url_params = edq.net.util.parse_query_string(parts.query)
            for (key, value) in url_params.items():
                if (key not in parameters):
                    parameters[key] = value

        if (url_path is None):
            raise ValueError('URL path cannot be empty, it must be explicitly set via `url_path`, or indirectly via `url`.')

        # Sort parameter keys for consistency.
        parameters = {key: parameters[key] for key in sorted(parameters.keys())}

        return url_path, url_anchor, parameters

    def resolve_paths(self, base_dir: str) -> None:
        """ Resolve any paths relative to the given base dir. """

        for file_info in self.files:
            file_info.resolve_path(base_dir)

    def match(self, query: 'HTTPExchange',
            match_headers: bool = True,
            headers_to_skip: typing.Union[typing.List[str], None] = None,
            params_to_skip: typing.Union[typing.List[str], None] = None,
            **kwargs: typing.Any) -> typing.Tuple[bool, typing.Union[str, None]]:
        """
        Check if this exchange matches the query exchange.
        If they match, `(True, None)` will be returned.
        If they do not match, `(False, <hint>)` will be returned, where `<hint>` points to where the mismatch is.

        Note that this is not an equality check,
        as a query exchange is often missing the response components.
        This method is often invoked the see if an incoming HTTP request (the query) matches an existing exchange.
        """

        if (query.method != self.method):
            return False, f"HTTP method does not match (query = {query.method}, target = {self.method})."

        if (query.url_path != self.url_path):
            return False, f"URL path does not match (query = {query.url_path}, target = {self.url_path})."

        if (query.url_anchor != self.url_anchor):
            return False, f"URL anchor does not match (query = {query.url_anchor}, target = {self.url_anchor})."

        if (headers_to_skip is None):
            headers_to_skip = edq.net.settings.get_exchanges_ignore_headers()

        if (params_to_skip is None):
            params_to_skip = []

        if (match_headers):
            match, hint = self._match_dict('header', query.headers, self.headers, headers_to_skip)
            if (not match):
                return False, hint

        match, hint = self._match_dict('parameter', query.parameters, self.parameters, params_to_skip)
        if (not match):
            return False, hint

        # Check file names and hash contents.
        query_filenames = {(file.name, file.hash_content()) for file in query.files}
        target_filenames = {(file.name, file.hash_content()) for file in self.files}
        if (query_filenames != target_filenames):
            return False, f"File names do not match (query = {query_filenames}, target = {target_filenames})."

        return True, None

    def _match_dict(self,
            label: str,
            query_dict: typing.Dict[str, typing.Any],
            target_dict: typing.Dict[str, typing.Any],
            keys_to_skip: typing.Union[typing.List[str], None] = None,
            query_label: str = 'query',
            target_label: str = 'target',
            normalize_key_case: bool = True,
            ) -> typing.Tuple[bool, typing.Union[str, None]]:
        """ A subcheck in match(), specifically for a dictionary. """

        if (keys_to_skip is None):
            keys_to_skip = []

        if (normalize_key_case):
            keys_to_skip = [key.lower() for key in keys_to_skip]
            query_dict = {key.lower(): value for (key, value) in query_dict.items()}
            target_dict = {key.lower(): value for (key, value) in target_dict.items()}

        query_keys = set(query_dict.keys()) - set(keys_to_skip)
        target_keys = set(target_dict.keys()) - set(keys_to_skip)

        if (query_keys != target_keys):
            return False, f"{label.title()} keys do not match ({query_label} = {query_keys}, {target_label} = {target_keys})."

        for key in sorted(query_keys):
            query_value = query_dict[key]
            target_value = target_dict[key]

            if (query_value != target_value):
                comparison = f"{query_label} = '{query_value}', {target_label} = '{target_value}'"
                return False, f"{label.title()} '{key}' has a non-matching value ({comparison})."

        return True, None

    def get_url(self) -> str:
        """ Get the URL path and anchor combined. """

        url = self.url_path

        if (self.url_anchor is not None):
            url += ('#' + self.url_anchor)

        return url

    def match_response(self,
            response: requests.Response,
            override_body: typing.Union[str, None] = None,
            headers_to_skip: typing.Union[typing.List[str], None] = None,
            **kwargs: typing.Any) -> typing.Tuple[bool, typing.Union[str, None]]:
        """
        Check if this exchange matches the given response.
        If they match, `(True, None)` will be returned.
        If they do not match, `(False, <hint>)` will be returned, where `<hint>` points to where the mismatch is.
        """

        if (headers_to_skip is None):
            headers_to_skip = edq.net.settings.get_exchanges_ignore_headers()

        response_body = override_body
        if (response_body is None):
            response_body = response.text

        if (self.response_code != response.status_code):
            return False, f"http status code does match (expected: {self.response_code}, actual: {response.status_code})"

        expected_body = self.response_body
        actual_body = None

        if (self.json_body):
            actual_body = response.json()

            # Normalize the actual and expected bodies.

            actual_body = edq.util.json.dumps(actual_body)

            if (isinstance(expected_body, str)):
                expected_body = edq.util.json.loads(expected_body)

            expected_body = edq.util.json.dumps(expected_body)
        else:
            actual_body = response_body

        if (self.response_body != actual_body):
            body_hint = f"expected: '{self.response_body}', actual: '{actual_body}'"
            return False, f"body does not match ({body_hint})"

        response_headers = {key.lower().strip(): value for (key, value) in response.headers.items()}
        match, hint = self._match_dict('header', response_headers, self.response_headers,
                keys_to_skip = headers_to_skip,
                query_label = 'response', target_label = 'exchange')

        if (not match):
            return False, hint

        return True, None

    def compute_relpath(self, http_exchange_extension: str = DEFAULT_HTTP_EXCHANGE_EXTENSION) -> str:
        """ Create a consistent, semi-unique, and relative path for this exchange. """

        url = self.get_url().strip()
        parts = url.split('/')

        if (url in ['', '/']):
            filename = '_index_'
            dirname = ''
        else:
            filename = parts[-1]

            if (len(parts) > 1):
                dirname = os.path.join(*parts[0:-1])
            else:
                dirname = ''

        parameters = {}
        for key in sorted(self.parameters.keys()):
            parameters[key] = self.parameters[key]

        # Treat files as params as well.
        for file_info in self.files:
            parameters[f"file-{file_info.name}"] = file_info.hash_content()

        query = urllib.parse.urlencode(parameters)
        if (query != ''):
            # The query can get very long, so we may have to clip it.
            query_text = edq.util.hash.clip_text(query, QUERY_CLIP_LENGTH)

            # Note that the '?' is URL encoded.
            filename += f"%3F{query_text}"

        filename += f"_{self.method}{http_exchange_extension}"

        return os.path.join(dirname, filename)

    def to_dict(self,
            context: typing.Union[edq.util.serial.SerializationContext, None] = None,
            ) -> typing.Dict[str, typing.Any]:
        return vars(self)

    @classmethod
    def from_dict(cls,
            data: typing.Dict[str, typing.Any],
            context: typing.Union[edq.util.serial.SerializationContext, None] = None,
            ) -> typing.Any:
        return HTTPExchange(**data)

    @classmethod
    def from_path(cls,
            path: str,
            context: typing.Union[edq.util.serial.SerializationContext, None] = None,
            ) -> 'HTTPExchange':
        """
        Load an exchange from a file.
        This will also handle setting the exchanges source path (if specified) and resolving the exchange's paths.
        """

        if (context is None):
            context = edq.util.serial.SerializationContext()

        exchange = super().from_path(path, context)

        set_source_path = edq.util.parse.soft_boolean(context.extra.get('set_source_path', True))
        if (set_source_path is True):
            exchange.source_path = os.path.abspath(path)

        exchange.resolve_paths(os.path.abspath(os.path.dirname(path)))  # pylint: disable=no-member

        return exchange

    @classmethod
    def from_response(cls,
            response: requests.Response,
            headers_to_skip: typing.Union[typing.List[str], None] = None,
            params_to_skip: typing.Union[typing.List[str], None] = None,
            allow_redirects: typing.Union[bool, None] = None,
            clean_response_func: typing.Union[str, None] = None,
            finalize_func: typing.Union[str, None] = None,
            ) -> 'HTTPExchange':
        """ Create a full exchange from a response. """

        if (headers_to_skip is None):
            headers_to_skip = edq.net.settings.get_exchanges_ignore_headers()

        if (params_to_skip is None):
            params_to_skip = []

        if (clean_response_func is None):
            clean_response_func = edq.net.settings.get_exchanges_clean_response_func()

        if (finalize_func is None):
            finalize_func = edq.net.settings.get_exchanges_finalize_func()

        body = response.text

        # Use a clean function (if one exists).
        if (clean_response_func is not None):
            # Make a copy of the response to avoid cleaning functions modifying it.
            # Note that this is not a very complete solution, since we can't rely on the deep copy getting everything right.
            response = copy.deepcopy(response)

            modify_func = edq.util.pyimport.fetch(clean_response_func)
            body = modify_func(response, body)

        request_headers = {key.lower().strip(): value for (key, value) in response.request.headers.items()}
        response_headers = {key.lower().strip(): value for (key, value) in response.headers.items()}

        request_data, request_files = edq.net.util.parse_request_data(
                response.request.url,
                request_headers,
                response.request.body)  # type: ignore[arg-type]

        # Clean headers.
        for key in headers_to_skip:
            key = key.lower()

            # Keep the location header if this is an allowed redirect.
            if (allow_redirects and (key == 'location') and (300 <= response.status_code < 400)):
                continue

            request_headers.pop(key, None)
            response_headers.pop(key, None)

        # Clean parameters.
        for key in params_to_skip:
            request_data.pop(key, None)

        files = [FileInfo(name = name, content = content) for (name, content) in request_files.items()]

        data: typing.Dict[str, typing.Any] = {
            'method': response.request.method,
            'url': response.request.url,
            'url_anchor': response.request.headers.get(edq.net.settings.ANCHOR_HEADER_KEY, None),
            'parameters': request_data,
            'files': files,
            'headers': request_headers,
            'response_code': response.status_code,
            'response_headers': response_headers,
            'response_body': body,
            'response_modifier': clean_response_func,
            'allow_redirects': allow_redirects,
        }

        exchange = HTTPExchange(**data)

        # Use a finalize function (if one exists).
        if (finalize_func is not None):
            finalize_func_object = edq.util.pyimport.fetch(finalize_func)

            exchange = finalize_func_object(exchange)
            exchange.finalize = finalize_func

        return exchange

@typing.runtime_checkable
class HTTPExchangeResponseCleanFunc(typing.Protocol):
    """
    A function that can be used to clean a response before creating an exchange.
    """

    def __call__(self,
            response: requests.Response,
            body: str,
            ) -> str:
        """
        Take in a response and response body.
        Clean the response in-place and return the new body.
        """

@typing.runtime_checkable
class HTTPExchangeFinalizeFunc(typing.Protocol):
    """
    A function that can be used to finalize an exchange.
    """

    def __call__(self,
            exchange: HTTPExchange
            ) -> HTTPExchange:
        """
        Take in an exchange, finalize it, and pass back the finalized exchange (which may be different than the input one).
        """

@typing.runtime_checkable
class HTTPExchangeComplete(typing.Protocol):
    """
    A function that can be called after a request has been made (and exchange constructed).
    """

    def __call__(self,
            exchange: HTTPExchange
            ) -> str:
        """
        Called after an HTTP exchange has been completed.
        """
