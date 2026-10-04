"""
Unset the first matching instance of a configuration option.

Does nothing if there is no matching config.
"""

import argparse
import os
import typing

import edq.config.argparser
import edq.config.load
import edq.config.util

def run(args: argparse.Namespace) -> int:
    """ Run the target command and return the suggested exit status. """

    if ((args.scope_file is not None) and (not (edq.util.dirent.exists(args.scope_file)))):
        print(f"Specified config file does not exist: '{os.path.abspath(args.scope_file)}'.")
        return 1

    for key in args.config_to_unset:
        path = args.scope_file
        if (path is None):
            path = _get_path_from_source(key, args)

        if (path is None):
            print(f"Could not find a file where '{key}' was set.")
            continue

        path = os.path.abspath(path)
        edq.config.util.remove_options_in_config_file(path, [key])
        print(f"Unset config option ('{key}') from: '{path}'.")

    return 0

def modify_parser(parser: argparse.ArgumentParser) -> None:
    """ Add this CLI's flags to the given parser. """

    parser.add_argument('config_to_unset', metavar = "KEY",
        action = 'store', nargs = '+', type = str,
        help = ("Configuration key to unset."),
    )

    edq.config.argparser.add_config_location_argument_group(parser)

def _get_path_from_source(key: str, args: argparse.Namespace) -> typing.Union[str, None]:
    """ Look through a key's sources for the first file-based entry that matches the specified config. """

    for source in args._config_info.sources.get(key, []):
        source = typing.cast(edq.config.load.ConfigLoadResult, source)

        if (source.path is None):
            continue

        # If nothing was specified, match the first path.
        if ((not args.scope_local) and (not args.scope_project) and (not args.scope_global)):
            return source.path

        if (args.scope_local and isinstance(source.spec, edq.config.source.LocalSpec)):
            return source.path

        if (args.scope_project and isinstance(source.spec, edq.config.source.ProjectSpec)):
            return source.path

        if (args.scope_global and isinstance(source.spec, edq.config.source.GlobalSpec)):
            return source.path

    return None
