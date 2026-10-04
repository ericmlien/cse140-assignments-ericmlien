"""
Profile some Python target using Python's cprofile stdlib.
"""

import argparse
import os
import shutil
import sys

import pyflame.sampler

import edq.core.argparser
import edq.util.dirent
import edq.util.profile

FLAMEGRAPH_URL: str = 'https://github.com/brendangregg/FlameGraph/blob/master/flamegraph.pl'

DEFAULT_FLAMEGRAPH_PATH: str = 'flamegraph.pl'
DEFAULT_OUTPUT_PATH: str = 'flame.svg'
DEFAULT_SAMPLE_INTERVAL_SECS: float = 0.000001

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    flamegraph_path = shutil.which(args.flamegraph_path)
    if (flamegraph_path is None):
        # Check for relative paths.
        if (os.path.exists(args.flamegraph_path)):
            flamegraph_path = os.path.abspath(args.flamegraph_path)
        else:
            raise ValueError(f"Failed to find flamegraph script ('{args.flamegraph_path}'), download from '{FLAMEGRAPH_URL}'.")

    flamegraph_extra_args = [
        '--width', '2000',
    ]

    sampler = pyflame.sampler.Sampler(args.sample_interval_secs)
    edq.util.profile.exec_for_profile(args.run_target, imports = args.imports, is_module = args.module, module_args = args.module_args)
    stack_counts = sampler.stop()

    svg_text = pyflame.render.stack_counts_to_svg(stack_counts, flamegraph_path, flamegraph_extra_args)
    edq.util.dirent.write_file(args.out_path, svg_text)

    print(f"Wrote flamegraph to '{args.out_path}'.")

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

    parser.add_argument('--import', dest = 'imports',
        action = 'append', default = [],
        help = 'Import this module before running the command.')

    parser.add_argument('--out', dest = 'out_path',
        action = 'store', type = str, default = DEFAULT_OUTPUT_PATH,
        help = 'The path where the output famegraph will be written (default: %(default)s).')

    parser.add_argument('--flamegraph-path', dest = 'flamegraph_path',
        action = 'store', type = str, default = DEFAULT_FLAMEGRAPH_PATH,
        help = 'The path (or name in $PATH) of the flamegraph script (default: %(default)s).')

    parser.add_argument('--sample-interval', dest = 'sample_interval_secs',
        action = 'store', type = float, default = DEFAULT_SAMPLE_INTERVAL_SECS,
        help = 'The number of seconds between samples (default: %(default)s).')

    return parser

if (__name__ == '__main__'):
    sys.exit(main())
