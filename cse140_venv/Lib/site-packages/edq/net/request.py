import http
import logging
import os
import time
import typing
import urllib.parse
import urllib3

import requests

import edq.core.errors
import edq.net.exchange
import edq.net.exchangeserver
import edq.net.settings
import edq.util.dirent
import edq.util.encoding
import edq.util.json
import edq.util.pyimport

_logger = logging.getLogger(__name__)

RETRY_BACKOFF_SECS: float = 0.5
""" A back-off factor between failed network requests. """

@typing.runtime_checkable
class ResponseModifierFunction(typing.Protocol):
    """
    A function that can be used to modify an exchange's response.
    Exchanges can use these functions to normalize their responses before saving.
    """

    def __call__(self,
            response: requests.Response,
            body: str,
            ) -> str:
        """
        Modify the http response.
        Headers may be modified in the response directly,
        while the modified (or same) body must be returned.
        """

def make_request(method: str, url: str,
        headers: typing.Union[typing.Dict[str, typing.Any], None] = None,
        data: typing.Union[typing.Dict[str, typing.Any], None] = None,
        files: typing.Union[typing.List[typing.Any], None] = None,
        raise_for_status: bool = True,
        timeout_secs: typing.Union[float, typing.Tuple[float, float], None] = None,
        output_dir: typing.Union[str, None] = None,
        send_anchor_header: bool = True,
        headers_to_skip: typing.Union[typing.List[str], None] = None,
        params_to_skip: typing.Union[typing.List[str], None] = None,
        http_exchange_extension: str = edq.net.exchange.DEFAULT_HTTP_EXCHANGE_EXTENSION,
        add_http_prefix: bool = True,
        additional_requests_options: typing.Union[typing.Dict[str, typing.Any], None] = None,
        allow_redirects: typing.Union[bool, None] = True,
        retries: int = 0,
        https_verification: typing.Union[bool, None] = None,
        request_complete_callback: typing.Union[edq.net.exchange.HTTPExchangeComplete, None] = None,
        **kwargs: typing.Any) -> typing.Tuple[requests.Response, str]:
    """
    Make an HTTP request and return the response object and text body.

    For `timeout_secs`, see: https://docs.python-requests.org/en/latest/user/advanced/#timeouts
    """

    if (add_http_prefix and (not url.lower().startswith('http'))):
        url = 'http://' + url

    retries = max(0, retries)

    if (output_dir is None):
        output_dir = edq.net.settings.get_exchanges_out_dir()

    if (headers is None):
        headers = {}

    if (data is None):
        data = {}

    if (files is None):
        files = []

    if (additional_requests_options is None):
        additional_requests_options = {}

    if (request_complete_callback is None):
        raw_callback = edq.net.settings.get_request_complete_callback()
        if (raw_callback is not None):
            request_complete_callback = typing.cast(edq.net.exchange.HTTPExchangeComplete, raw_callback)

    # Add in the anchor as a header (since it is not traditionally sent in an HTTP request).
    if (send_anchor_header):
        headers = headers.copy()

        parts = urllib.parse.urlparse(url)
        headers[edq.net.settings.ANCHOR_HEADER_KEY] = parts.fragment.lstrip('#')

    # Compute the full connection/read timeout.
    if (timeout_secs is None):
        timeout_secs = (edq.net.settings.get_connection_timeout_secs(), edq.net.settings.get_read_timeout_secs())
    elif (isinstance(timeout_secs, float)):
        timeout_secs = (timeout_secs, timeout_secs)

    options: typing.Dict[str, typing.Any] = {
        'timeout': timeout_secs,
    }

    # Check for HTTPS verification.
    if ((https_verification is False) or ((https_verification is None) and (not edq.net.settings.get_https_verification()))):
        options['verify'] = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    options.update(additional_requests_options)

    options.update({
        'headers': headers,
        'files': files,
    })

    if (allow_redirects is False):
        options['allow_redirects'] = False

    if (method == 'GET'):
        options['params'] = data
    else:
        options['data'] = data

    _logger.debug("Making %s request: '%s' (options = %s).", method, url, options)
    response = _make_request_with_retry(method, url, options, retries)

    body = response.text
    if (_logger.level <= logging.DEBUG):
        log_body = body
        if (response.encoding is None):
            log_body = f"<hash> {edq.util.hash.sha256_hex(response.content)}"

        _logger.debug("Response:\n%s", log_body)

    if (raise_for_status):
        # Handle 404s a little special, as their body may contain useful information.
        if ((response.status_code == http.HTTPStatus.NOT_FOUND) and (body is not None) and (body.strip() != '')):
            response.reason += f" (Body: '{body.strip()}')"

        response.raise_for_status()

    exchange = None
    if ((output_dir is not None) or (request_complete_callback is not None)):
        exchange = edq.net.exchange.HTTPExchange.from_response(
            response,
            headers_to_skip = headers_to_skip,
            params_to_skip = params_to_skip,
            allow_redirects = options.get('allow_redirects', True),
        )

        if (output_dir is not None):
            _write_exchange(exchange, output_dir, http_exchange_extension)

            # Also write any redirects.
            for redirect_response in response.history:
                redirect_exchange = edq.net.exchange.HTTPExchange.from_response(
                    redirect_response,
                    headers_to_skip = headers_to_skip,
                    params_to_skip = params_to_skip,
                    allow_redirects = options.get('allow_redirects', True),
                )
                _write_exchange(redirect_exchange, output_dir, http_exchange_extension)

        if (request_complete_callback is not None):
            request_complete_callback(exchange)

    return response, body

def _write_exchange(exchange: edq.net.exchange.HTTPExchange, output_dir: str, http_exchange_extension: str) -> None:
    """ Write an exchange to disk in the computed path. """

    relpath = exchange.compute_relpath(http_exchange_extension = http_exchange_extension)
    path = os.path.abspath(os.path.join(output_dir, relpath))

    edq.util.dirent.mkdir(os.path.dirname(path))
    edq.util.json.dump_path(exchange, path, indent = 4, sort_keys = False)

def make_with_exchange(
        exchange: edq.net.exchange.HTTPExchange,
        base_url: str,
        raise_for_status: bool = True,
        **kwargs: typing.Any,
        ) -> typing.Tuple[requests.Response, str]:
    """ Perform the HTTP request described by the given exchange. """

    files = []
    for file_info in exchange.files:
        content = file_info.content

        # Content is base64 encoded.
        if (file_info.b64_encoded and isinstance(content, str)):
            content = edq.util.encoding.from_base64(content)

        # Content is missing and must be in a file.
        if (content is None):
            content = open(file_info.path, 'rb')  # type: ignore[assignment,arg-type]  # pylint: disable=consider-using-with

        files.append((file_info.name, content))

    url = f"{base_url}/{exchange.get_url()}"

    response, body = make_request(exchange.method, url,
            headers = exchange.headers,
            data = exchange.parameters,
            files = files,
            raise_for_status = raise_for_status,
            allow_redirects = exchange.allow_redirects,
            **kwargs,
    )

    if (exchange.response_modifier is not None):
        modify_func = edq.util.pyimport.fetch(exchange.response_modifier)
        body = modify_func(response, body)

    return response, body


def make_get(url: str, **kwargs: typing.Any) -> typing.Tuple[requests.Response, str]:
    """
    Make a GET request and return the response object and text body.
    """

    return make_request('GET', url, **kwargs)

def make_post(url: str, **kwargs: typing.Any) -> typing.Tuple[requests.Response, str]:
    """
    Make a POST request and return the response object and text body.
    """

    return make_request('POST', url, **kwargs)

def _make_request_with_retry(
        method: str,
        url: str,
        options: typing.Dict[str, typing.Any],
        retries: int,
        ) -> requests.Response:
    """ Make a request, retrying on failure. """

    # Try once and then the number of allowed retries.
    attempt_count = 1 + retries

    errors = []
    for attempt_index in range(attempt_count):
        if (attempt_index > 0):
            # Wait before the next retry.
            time.sleep(attempt_index * RETRY_BACKOFF_SECS)

        try:
            response = requests.request(method, url, **options)  # pylint: disable=missing-timeout
            break
        except Exception as ex:
            errors.append(ex)

    if (len(errors) == attempt_count):
        raise edq.core.errors.RetryError(f"HTTP {method} for '{url}'", attempt_count, retry_errors = errors)

    return response
