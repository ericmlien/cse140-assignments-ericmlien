import cProfile
import pstats
import runpy
import sys
import typing

import edq.util.dirent
import edq.util.pyimport

def exec_for_profile(
        run_target: str,
        imports: typing.Union[typing.List[str], None] = None,
        is_module: bool = False,
        module_args: typing.Union[typing.List[str], None] = None,
        ) -> None:
    """
    Exec the specified code for use in a profiler.
    This does not profile the code, only exec's it.

    Note that this function is calling exec(), which is dangerous for unknown code.
    You should only profile your own code.
    """

    if (imports is None):
        imports = []

    if (module_args is None):
        module_args = []

    profile_globals = globals().copy()
    for name in imports:
        profile_globals[name] = edq.util.pyimport.import_name(name)

    old_argv = sys.argv.copy()

    command = run_target
    if (is_module):
        profile_globals['run_module'] = runpy.run_module
        profile_globals['modname'] = run_target
        sys.argv = [run_target] + module_args

        command = "run_module(modname, run_name = '__main__')"

    try:
        exec(command, profile_globals, None)  # pylint: disable=exec-used
    except SystemExit:
        # Ignore exists.
        pass
    finally:
        sys.argv = old_argv

def cprofile(
        run_target: str,
        imports: typing.Union[typing.List[str], None] = None,
        is_module: bool = False,
        module_args: typing.Union[typing.List[str], None] = None,
        ) -> pstats.Stats:
    """ Profile some code and get stats back. """

    profiler = cProfile.Profile()
    profiler.enable()

    exec_for_profile(run_target, imports = imports, is_module = is_module, module_args = module_args)

    profiler.disable()

    return pstats.Stats(profiler)
