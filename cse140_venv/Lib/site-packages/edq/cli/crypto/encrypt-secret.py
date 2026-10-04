# pylint: disable=invalid-name

"""
Encrypt a cleartext string as an edq.util.crypto.Secret.

The standard configuration encryption key will be used.
"""

import argparse
import sys

import edq.config.constants
import edq.core.argparser
import edq.util.crypto

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    secret = edq.util.crypto.Secret(args.cleartext, iv_b64 = args.iv, salt_b64 = args.salt)
    ciphertext = secret.encrypt(args._config_info.application_config.encryption_key)

    print(ciphertext)

    return 0

def main() -> int:
    """ Get a parser, parse the args, and call run. """
    return run_cli(_get_parser().parse_args())

def _get_parser() -> argparse.ArgumentParser:
    """ Get the parser. """

    parser = edq.core.argparser.get_default_parser(__doc__.strip())

    parser.add_argument('cleartext', metavar = 'TEXT',
        action = 'store', type = str,
        help = 'The text to encrypt.')

    parser.add_argument('--encryption-method', dest = 'encryption_method',
        action = 'store', type = str, default = edq.util.crypto.EncryptionMethod.AES256v1.value,
        choices = [choice.value for choice in edq.util.crypto.EncryptionMethod],
        help = 'The encryption method to use (default: %(default)s).')

    parser.add_argument('--salt', dest = 'salt',
        action = 'store', type = str, default = None,
        help = ('An optional salt to provide (as a base64 encoded string).'
                + ' Providing a salt is not recommended.'
                + ' If no salt is provided, one will be generated randomly.')
    )

    parser.add_argument('--iv', dest = 'iv',
        action = 'store', type = str, default = None,
        help = ('An optional initialization vector (IV) to provide (as a base64 encoded string).'
                + ' Providing an IV is not recommended.'
                + ' If no IV is provided, one will be generated randomly.')
    )

    return parser

if (__name__ == '__main__'):
    sys.exit(main())
