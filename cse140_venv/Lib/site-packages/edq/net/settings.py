# pylint: disable=global-statement,invalid-name

"""
This module holds options that persist the lifetime of the program.
Most options can be overwritten in specific calls, e.g., in edq.net.request.make_request().
"""

import typing

ANCHOR_HEADER_KEY: str = 'edq-anchor'
"""
By default, requests made via make_request() will send a header with this key that includes the anchor component of the URL.
Anchors are not traditionally sent in requests, but this will allow exchanges to capture this extra piece of information.
"""

DEFAULT_HTTPS_VERIFICATION: bool = True

DEFAULT_CONNECTION_TIMEOUT_SECS: float = 30.0

DEFAULT_READ_TIMEOUT_SECS: float = 60.0 * 30

DEFAULT_EXCHANGES_IGNORE_HEADERS: typing.List[str] = [
    'accept',
    'accept-encoding',
    'accept-language',
    'access-control-allow-origin',
    'access-control-allow-credentials',
    'access-control-allow-methods',
    'access-control-request-method',
    'access-control-allow-headers',
    'cache-control',
    'connection',
    'content-length',
    'content-security-policy',
    'content-type',
    'cookie',
    'date',
    'dnt',
    'etag',
    'host',
    'link',
    'location',  # Will be specially kept on allowed redirects.
    'pragma',
    'priority',
    'referrer-policy',
    'sec-fetch-dest',
    'sec-fetch-mode',
    'sec-fetch-site',
    'sec-fetch-user',
    'sec-gpc',
    'server',
    'server-timing',
    'set-cookie',
    'upgrade-insecure-requests',
    'user-agent',
    'x-content-type-options',
    'x-download-options',
    'x-permitted-cross-domain-policies',
    'x-rate-limit-remaining',
    'x-request-context-id',
    'x-request-cost',
    'x-runtime',
    'x-session-id',
    'x-xss-protection',
    ANCHOR_HEADER_KEY,
]

_exchanges_ignore_headers: typing.List[str] = DEFAULT_EXCHANGES_IGNORE_HEADERS.copy()
"""
By default, ignore these headers during exchange matching.
Some are sent automatically and we don't need to record (like content-length),
and some are additional information we don't need.
"""

_exchanges_out_dir: typing.Union[str, None] = None
""" If not None, all requests made via make_request() will be saved as an HTTPExchange in this directory. """

_exchanges_clean_response_func: typing.Union[str, None] = None
"""
If not None, this function reference will be used to clean responses (and bodies)
before creating an exchange with edq.net.exchange.HTTPExchange.from_response().

This reference must be importable via edq.util.pyimport.fetch().
String references are used instead of actual function references because these values will be stored inside the exchange.
The referenced function should follow the edq.net.exchange.HTTPExchangeResponseCleanFunc protocol.
"""

_exchanges_finalize_func: typing.Union[str, None] = None
"""
If not None, all exchanges created with edq.net.exchange.HTTPExchange.from_response()
will have this function reference called before returning the created exchange.

This reference must be importable via edq.util.pyimport.fetch().
String references are used instead of actual function references because these values will be stored inside the exchange.
The referenced function should follow the edq.net.exchange.HTTPExchangeFinalizeFunc protocol.
"""

_http_verification: bool = DEFAULT_HTTPS_VERIFICATION
"""
Whether to verify HTTPS requests.
Should be set to false when using fake/testing certificates.
"""

_connection_timeout_secs: float = DEFAULT_CONNECTION_TIMEOUT_SECS
""" The timeout for establishing a connection. """

_read_timeout_secs: float = DEFAULT_READ_TIMEOUT_SECS
""" The timeout for reading from a connection. """

_request_complete_callback: typing.Union[typing.Callable, None] = None  # pylint: disable=invalid-name
"""
If not None, call this func when make_request() is about to end.
This function should follow the edq.net.exchange.HTTPExchangeComplete protocol.
"""

def get_exchanges_clean_response_func() -> typing.Union[str, None]:
    """ Get the clean response func for exchanges. """

    return _exchanges_clean_response_func

def set_exchanges_clean_response_func(value: typing.Union[str, None] = None) -> None:
    """ Set the clean response func for exchanges. """

    global _exchanges_clean_response_func
    _exchanges_clean_response_func = value

def get_exchanges_finalize_func() -> typing.Union[str, None]:
    """ Get the finalize func for exchanges. """

    return _exchanges_finalize_func

def set_exchanges_finalize_func(value: typing.Union[str, None] = None) -> None:
    """ Set the finalize func for exchanges. """

    global _exchanges_finalize_func
    _exchanges_finalize_func = value

def get_exchanges_ignore_headers() -> typing.List[str]:
    """ Get the exchange headers to ignore. """

    return _exchanges_ignore_headers

def set_exchanges_ignore_headers(value: typing.Union[typing.List[str], None] = None) -> None:
    """ Set the exchange headers to ignore. """

    global _exchanges_ignore_headers

    if (value is None):
        value = DEFAULT_EXCHANGES_IGNORE_HEADERS.copy()

    _exchanges_ignore_headers = value

def get_exchanges_out_dir() -> typing.Union[str, None]:
    """ Get the directory to write HTTP exchanges (if any). """

    return _exchanges_out_dir

def set_exchanges_out_dir(value: typing.Union[str, None] = None) -> None:
    """ Set the directory to write HTTP exchanges. """

    global _exchanges_out_dir
    _exchanges_out_dir = value

def get_https_verification() -> bool:
    """ Get whether to check the SSL certificate for HTTPS requests. """

    return _http_verification

def set_https_verification(value: typing.Union[bool, None] = None) -> None:
    """ Set whether to check the SSL certificate for HTTPS requests. """

    global _http_verification

    if (value is None):
        value = DEFAULT_HTTPS_VERIFICATION

    _http_verification = value

def get_connection_timeout_secs() -> float:
    """ Get the timeout for establishing a connection. """

    return _connection_timeout_secs

def set_connection_timeout_secs(value: typing.Union[float, None] = None) -> None:
    """ Set the timeout for establishing a connection. """

    global _connection_timeout_secs

    if (value is None):
        value = DEFAULT_CONNECTION_TIMEOUT_SECS

    _connection_timeout_secs = value

def get_read_timeout_secs() -> float:
    """ Get the timeout for reading from a connection. """

    return _read_timeout_secs

def set_read_timeout_secs(value: typing.Union[float, None] = None) -> None:
    """ Set the timeout for reading from a connection. """

    global _read_timeout_secs

    if (value is None):
        value = DEFAULT_READ_TIMEOUT_SECS

    _read_timeout_secs = value

def get_request_complete_callback() -> typing.Union[typing.Callable, None]:
    """ Get the make_request() callback. """

    return _request_complete_callback

def set_request_complete_callback(value: typing.Union[typing.Callable, None] = None) -> None:
    """ Set the make_request() callback. """

    global _request_complete_callback
    _request_complete_callback = value
