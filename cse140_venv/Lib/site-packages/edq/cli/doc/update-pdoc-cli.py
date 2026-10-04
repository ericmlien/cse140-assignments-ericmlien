# pylint: disable=invalid-name

"""
Insert CLI documentation into built pdoc HTML documentation.
"""

import argparse
import sys

import edq.clilib.pdoc
import edq.core.argparser

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    edq.clilib.pdoc.update_pdoc(args.python_package, args.base_qualified_name, args.html_dir)

    return 0

def main() -> int:
    """ Get a parser, parse the args, and call run. """

    return run_cli(_get_parser().parse_args())

def _get_parser() -> argparse.ArgumentParser:
    """ Get a parser and add addition flags. """

    parser = edq.core.argparser.get_default_parser(__doc__.strip())

    parser.add_argument('python_package', metavar = 'PYTHON_PACKAGE',
        action = 'store', type = str,
        help = 'The package to search for CLI files, e.g., "edq/cli".',
    )

    parser.add_argument('base_qualified_name', metavar = 'PYTHON_QUALIFIED_NAME',
        action = 'store', type = str,
        help = 'The qualified name to append to all python objects to recover their fully qualified name, e.g., "edq.cli".',
    )

    parser.add_argument('html_dir', metavar = 'HTML_DOCS_DIR',
        action = 'store', type = str,
        help = 'The directory containing already build pdoc documentation.',
    )

    return parser

if (__name__ == '__main__'):
    sys.exit(main())
