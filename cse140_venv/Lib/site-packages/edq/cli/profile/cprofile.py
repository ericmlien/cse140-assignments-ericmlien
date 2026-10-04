"""
Profile some Python target using Python's cprofile stdlib.
"""

import argparse
import sys

import edq.core.argparser
import edq.util.profile

DEFAULT_ROW_COUNT: int = 50

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    stats = edq.util.profile.cprofile(args.run_target, imports = args.imports, is_module = args.module, module_args = args.module_args)

    print(f"--- BEGIN: All Functions, Sorted by Cumulative Time, Top {args.row_count} ---")
    stats.sort_stats('cumtime').print_stats(args.row_count)
    print(f"--- END: All Functions, Sorted by Cumulative Time, Top {args.row_count} ---")

    print(f"--- BEGIN: All Functions, Sorted by Total Time, Top {args.row_count} ---")
    stats.sort_stats('tottime').print_stats(args.row_count)
    print(f"--- END: All Functions, Sorted by Total Time, Top {args.row_count} ---")

    for (i, pattern) in enumerate(args.patterns):
        label = f"Pattern {i}: '{pattern}'"

        print(f"--- BEGIN: {label}, Sorted by Cumulative Time, Top {args.row_count} ---")
        stats.sort_stats('cumtime').print_stats(pattern, args.row_count)
        print(f"--- END: {label}, Sorted by Cumulative Time, Top {args.row_count} ---")

        print(f"--- BEGIN: {label}, Sorted by Total Time, Top {args.row_count} ---")
        stats.sort_stats('tottime').print_stats(pattern, args.row_count)
        print(f"--- END: {label}, Sorted by Total Time, Top {args.row_count} ---")

    return 0

def main() -> int:
    """ Get a parser, parse the args, and call run. """
    return run_cli(_get_parser().parse_args())

def _get_parser() -> argparse.ArgumentParser:
    """ Get the parser. """

    parser = edq.core.argparser.get_default_parser(__doc__.strip())

    parser.add_argument('run_target', metavar = 'RUN_TARGET',
        action = 'store', type = str,
        help = 'The code to profile.')

    parser.add_argument('module_args', metavar = 'MODULE_ARGS',
        action = 'store', type = str, nargs = '*',
        help = 'Additional args to pass to the target if `--module` is used.')

    parser.add_argument('--module', '-m', dest = 'module',
        action = 'store_true', default = False,
        help = 'Treat the provided run target as a module, and all other positional arguments are arguments to the module (default: %(default)s).')

    parser.add_argument('--count', dest = 'row_count',
        action = 'store', type = int, default = DEFAULT_ROW_COUNT,
        help = 'The maximum number of rows to show per result type (default: %(default)s).')

    parser.add_argument('--import', dest = 'imports',
        action = 'append', default = [],
        help = 'Import this module before running the command.')

    parser.add_argument('--pattern', dest = 'patterns',
        action = 'append', default = [],
        help = 'A function pattern to display output for.')

    return parser

if (__name__ == '__main__'):
    sys.exit(main())
