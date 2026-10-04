import os
import typing

import requests

import edq.net.exchange
import edq.net.exchangeserver
import edq.net.request
import edq.testing.unittest

class HTTPServerTest(edq.testing.unittest.BaseTest):
    """
    A unit test class that requires a testing HTTP server to be running.
    """

    server_key: str = ''
    """
    A key to indicate which test server this test class is using.
    By default all test classes share the same server,
    but child classes can set this if they want to control who is using the same server.
    If `tear_down_server` is true, then the relevant server will be stopped (and removed) on a call to tearDownClass(),
    which happens after a test class is complete.
    """

    tear_down_server: bool = True
    """
    Tear down the relevant test server in tearDownClass().
    If set to false then the server will never get torn down,
    but can be shared between child test classes.
    """

    skip_test_exchanges_base: bool = False
    """ Skip test_exchanges_base. """

    override_server_url: typing.Union[str, None] = None
    """ If set, return this URL from get_server_url(). """

    _servers: typing.Dict[str, edq.net.exchangeserver.HTTPExchangeServer] = {}
    """ The active test servers. """

    _complete_exchange_tests: typing.Set[str] = set()
    """
    Keep track of the servers (by key) that have run their test_exchanges_base.
    This test should only be run once per server.
    """

    _child_class_setup_called: bool = False
    """ Keep track if the child class setup was called. """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        if (not cls._child_class_setup_called):
            cls.child_class_setup()
            cls._child_class_setup_called = True

        if (cls.server_key in cls._servers):
            return

        server = cls.create_server()
        cls._servers[cls.server_key] = server

        cls.setup_server(server)
        server.start()
        cls.post_start_server(server)

    @classmethod
    def create_server(cls) -> edq.net.exchangeserver.HTTPExchangeServer:
        """ Create the actual exchange server. """

        return edq.net.exchangeserver.HTTPExchangeServer()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()

        if (cls.server_key not in cls._servers):
            return

        server = cls.get_server()

        if (cls.tear_down_server):
            server.stop()
            del cls._servers[cls.server_key]
            cls._complete_exchange_tests.discard(cls.server_key)

    @classmethod
    def suite_cleanup(cls) -> None:
        """ Cleanup all test servers. """

        for server in cls._servers.values():
            server.stop()

        cls._servers.clear()

    @classmethod
    def get_server(cls) -> edq.net.exchangeserver.HTTPExchangeServer:
        """ Get the current HTTP server or raise if there is no server. """

        server = cls._servers.get(cls.server_key, None)
        if (server is None):
            raise ValueError("Server has not been initialized.")

        return server

    @classmethod
    def child_class_setup(cls) -> None:
        """ This function is the recommended time for child classes to set any configuration. """

    @classmethod
    def setup_server(cls, server: edq.net.exchangeserver.HTTPExchangeServer) -> None:
        """ An opportunity for child classes to configure the test server before starting it. """

    @classmethod
    def post_start_server(cls, server: edq.net.exchangeserver.HTTPExchangeServer) -> None:
        """ An opportunity for child classes to work with the server after it has been started, but before any tests. """

    @classmethod
    def get_server_url(cls) -> str:
        """ Get the URL for this test's test server. """

        if (cls.override_server_url is not None):
            return cls.override_server_url

        server = cls.get_server()

        if (server.port is None):
            raise ValueError("Test server port has not been set.")

        return f"http://127.0.0.1:{server.port}"

    def assert_exchange(self, request: edq.net.exchange.HTTPExchange, response: edq.net.exchange.HTTPExchange,
            base_url: typing.Union[str, None] = None,
            ) -> requests.Response:
        """
        Assert that the result of making the provided request matches the provided response.
        The same HTTPExchange may be supplied for both the request and response.
        By default, the server's URL will be used as the base URL.
        The full response will be returned (if no assertion is raised).
        """

        server = self.get_server()

        if (base_url is None):
            base_url = self.get_server_url()

        full_response, body = edq.net.request.make_with_exchange(request, base_url, raise_for_status = True, **server.match_options)

        match, hint = response.match_response(full_response, override_body = body, **server.match_options)
        if (not match):
            raise AssertionError(f"Exchange does not match: '{hint}'.")

        return full_response

    def test_exchanges_base(self) -> None:
        """ Test making a request with each of the loaded exchanges. """

        # Check if this test has already been run for this server.
        if (self.server_key in self._complete_exchange_tests):
            # Don't skip the test (which will show up in the test output).
            # Instead, just return.
            return

        if (self.skip_test_exchanges_base):
            self.skipTest('test_exchanges_base has been manually skipped.')

        self._complete_exchange_tests.add(self.server_key)

        server = self.get_server()

        for (i, exchange) in enumerate(server.get_exchanges()):
            base_name = exchange.get_url()
            if (exchange.source_path is not None):
                base_name = os.path.splitext(os.path.basename(exchange.source_path))[0]

            with self.subTest(msg = f"Case {i} ({base_name}):"):
                self.assert_exchange(exchange, exchange)
