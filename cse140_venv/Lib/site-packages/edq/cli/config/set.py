"""
Shallow frontend for edq.config.cmd.set.
"""

import argparse
import sys

import edq.config.cmd.set
import edq.core.argparser

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    return edq.config.cmd.set.run(args)

def main() -> int:
    """ Get a parser, parse the args, and call run. """

    return run_cli(_get_parser().parse_args())

def _get_parser() -> argparse.ArgumentParser:
    """ Get a parser and add additional flags. """

    parser = edq.core.argparser.get_default_parser(edq.config.cmd.set.__doc__.strip())
    edq.config.cmd.set.modify_parser(parser)

    return parser

if (__name__ == '__main__'):
    sys.exit(main())
