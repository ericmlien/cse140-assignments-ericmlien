import argparse
import typing

import edq.net.exchange
import edq.net.request
import edq.net.settings

def set_cli_args(parser: argparse.ArgumentParser, extra_state: typing.Dict[str, typing.Any]) -> None:
    """
    Set common CLI arguments.
    This is a sibling to init_from_args(), as the arguments set here can be interpreted there.
    """

    group = parser.add_argument_group('network options')

    group.add_argument('--http-exchanges-out-dir', dest = 'http_exchanges_out_dir',
        action = 'store', type = str, default = None,
        help = 'If set, write all outgoing HTTP requests as exchanges to this directory.')

    group.add_argument('--https-no-verify', dest = 'https_no_verify',
        action = 'store_true', default = False,
        help = 'If set, skip HTTPS/SSL verification.')

def init_from_args(
        parser: argparse.ArgumentParser,
        args: argparse.Namespace,
        extra_state: typing.Dict[str, typing.Any]) -> None:
    """
    Take in args from a parser that was passed to set_cli_args(),
    and call init() with the appropriate arguments.
    """

    if (args.http_exchanges_out_dir is not None):
        edq.net.settings.set_exchanges_out_dir(args.http_exchanges_out_dir)

    if (args.https_no_verify):
        edq.net.settings.set_https_verification(False)
