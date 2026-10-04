"""
Show the CLI tools available in this package.
"""

import argparse
import inspect
import os

import edq.clilib.model
import edq.util.dirent
import edq.util.pyimport

def auto_list(
        recursive: bool = False,
        skip_dirs: bool = False,
        ) -> None:
    """
    Print the caller's docstring and call _list_dir() on it,
    but will figure out the package's docstring, base_dir, and command_prefix automatically.
    This will use the inspect library, so only use in places that use code normally.
    The first stack frame not in this file will be used.
    """

    this_path = os.path.realpath(__file__)

    caller_frame_info = None
    for frame_info in inspect.stack():
        if (edq.util.dirent.same(this_path, frame_info.filename)):
            # Ignore this file.
            continue

        caller_frame_info = frame_info
        break

    if (caller_frame_info is None):
        raise ValueError("Unable to determine caller's stack frame.")

    path = caller_frame_info.filename
    base_dir = os.path.dirname(path)

    try:
        module = inspect.getmodule(caller_frame_info.frame)
        if (module is None):
            raise ValueError(f"Unable to get module for '{path}'.")
    except Exception as ex:
        raise ValueError("Unable to get caller information for listing CLI information.") from ex

    if (module.__package__ is None):
        raise ValueError(f"Caller module has no package information: '{path}'.")

    package = edq.clilib.model.CLIPackage.from_path(base_dir, module.__package__)
    if (package is None):
        raise ValueError(f"Caller package is not a CLI package: '{base_dir}'.")

    print(package.get_description())
    _list_dir(package, recursive, skip_dirs)

def _list_dir(package: edq.clilib.model.CLIPackage, recursive: bool, skip_dirs: bool) -> None:
    """
    List/descend the given dir.
    Don't output information out this directory itself, just the entries.
    """

    for dirent in package.dirents:
        if (isinstance(dirent, edq.clilib.model.CLIModule)):
            _handle_module(dirent)
        elif (isinstance(dirent, edq.clilib.model.CLIPackage)):
            if (not skip_dirs):
                _handle_package(dirent)

            if (recursive):
                _list_dir(dirent, recursive, skip_dirs)

def _handle_module(module: edq.clilib.model.CLIModule) -> None:
    """ Process a module. """

    print()
    print(module.qualified_name)
    print(module.get_description())
    print(module.get_usage_text())

def _handle_package(package: edq.clilib.model.CLIPackage) -> None:
    """ Process a package. """

    print()
    print(package.qualified_name + '.*')
    print(package.get_description())
    print(f"See `python3 -m {package.qualified_name}` for more information.")

def _get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description = __doc__.strip(),
        epilog = ("Note that you don't need to provide a package as an argument,"
            + " since you already called this on the target package."))

    parser.add_argument('-r', '--recursive', dest = 'recursive',
        action = 'store_true', default = False,
        help = 'Recur into each package to look for tools and subpackages (default: %(default)s).')

    parser.add_argument('-s', '--skip-dirs', dest = 'skip_dirs',
        action = 'store_true', default = False,
        help = ('Do not output information about directories/packages,'
            + ' only tools/files/modules (default: %(default)s).'))

    return parser

def run_cli(args: argparse.Namespace) -> int:
    """
    List the caller's dir.
    """

    auto_list(recursive = args.recursive, skip_dirs = args.skip_dirs)

    return 0

def main() -> int:
    """
    Run as if this process has been called as a executable.
    This will parse the command line and list the caller's dir.
    """

    return run_cli(_get_parser().parse_args())
