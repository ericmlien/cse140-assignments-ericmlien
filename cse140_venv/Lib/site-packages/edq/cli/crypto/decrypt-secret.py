# pylint: disable=invalid-name

"""
Decrypt an edq.util.crypto.Secret into cleartext.

The standard configuration encryption key will be used.
"""

import argparse
import sys

import edq.config.constants
import edq.core.argparser
import edq.util.crypto

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    secret = edq.util.crypto.Secret.parse(args.ciphertext, args._config_info.application_config.encryption_key)

    print(secret.cleartext)

    return 0

def main() -> int:
    """ Get a parser, parse the args, and call run. """
    return run_cli(_get_parser().parse_args())

def _get_parser() -> argparse.ArgumentParser:
    """ Get the parser. """

    parser = edq.core.argparser.get_default_parser(__doc__.strip())

    parser.add_argument('ciphertext', metavar = 'TEXT',
        action = 'store', type = str,
        help = 'The ciphertext to decrypt.')

    return parser

if (__name__ == '__main__'):
    sys.exit(main())
