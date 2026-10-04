import argparse
import os
import typing

import edq.config.constants
import edq.config.load
import edq.config.settings
import edq.util.serial

def set_cli_args(
        parser: argparse.ArgumentParser,
        extra_state: typing.Dict[str, typing.Any],
        **kwargs: typing.Any,
        ) -> None:
    """
    Set common CLI arguments for configuration.
    """

    group = parser.add_argument_group('config options')

    group.add_argument('--config', dest = edq.config.constants.CONFIG_OPTIONS_KEY, metavar = "<KEY>=<VALUE>",
        action = 'append', type = str, default = [],
        help = ('Set a configuration option from the command-line.'
            + ' Specify options as <key>=<value> pairs.'
            + ' This flag can be specified multiple times.'
            + ' The options are applied in the order provided and later options override earlier ones.'
            + ' Will override options form all config files.')
    )

    group.add_argument('--config-file', dest = edq.config.constants.CONFIG_PATHS_KEY,
        action = 'append', type = str, default = [],
        help = ('Load config options from a JSON file.'
            + ' This flag can be specified multiple times.'
            + ' Files are applied in the order provided and later files override earlier ones.'
            + ' Will override options form both global and local config files.')
    )

    group.add_argument('--config-global', dest = edq.config.constants.GLOBAL_CONFIG_KEY,
        action = 'store', type = str, default = os.path.join(edq.config.settings.get_global_dir(), edq.config.settings.get_config_filename()),
        help = 'Set the default global config file path (default: %(default)s).',
    )

    group.add_argument('--encryption-key', dest = edq.config.constants.CONFIG_ENCRYPTION_KEY,
        action = 'store', type = str, default = None,
        help = 'Encryption key to use for configuration secrets (e.g., passwords and tokens).',
    )

    _attach_epilogue(parser)

def _attach_epilogue(parser: argparse.ArgumentParser) -> None:
    """
    Construct an epilogue detailing configuration information and attach it to the parser's epilogue.
    The epilogue will be created from the current config load order.
    Each source spec will be asked to create their portion of the epilogue.
    """

    load_order = edq.config.settings.get_load_order()
    if (len(load_order) == 0):
        return

    lines = [
        'Configuration is loaded into this program using a "tiered" system.',
        'This means that configuration options will be loaded from various sources in a pre-defined order.',
        'If the same value is read from multiple sources, then the **last** read value overrides any previous values.',
        'If you want to see where your configuration values are being loaded from, see the config list command with the `--show-origin` flag.',
        '',
        'Below is the order that configurations are read for this program:'
    ]

    indent = ' ' * edq.config.constants.DEFAULT_INDENT

    for (step_index, spec) in enumerate(load_order):
        spec_lines = spec.get_help_lines()
        if ((spec_lines is None) or (len(spec_lines) == 0)):
            continue

        for i in range(len(spec_lines)):  # pylint: disable=consider-using-enumerate
            # Add in a step number for this first line, and an indentation for all other lines..
            if (i == 0):
                spec_lines[i] = f"{step_index + 1}) {spec_lines[i]}"
            else:
                spec_lines[i] = indent + spec_lines[i]

        # Add another indentation level (for all lines).
        spec_lines = [indent + line for line in spec_lines]

        if (step_index != 0):
            lines.append('')

        lines += spec_lines

    # Prepare any existing epilogue.
    if (parser.epilog is None):
        parser.epilog = ''
    elif (len(parser.epilog) > 0):
        parser.epilog += "\n\n"

    lines = [indent + line for line in lines]
    parser.epilog += "CONFIGURATION\n\n" + "\n".join(lines)

def add_config_location_argument_group(parser: argparse.ArgumentParser) -> None:
    """ Add the configuration location argument group to the parser. """

    group = parser.add_argument_group("config location options").add_mutually_exclusive_group()

    group.add_argument('--local',
        action = 'store_true', dest = 'scope_local',
        help = ("Target config option(s) in a local config file.")
    )

    group.add_argument('--project',
        action = 'store_true', dest = 'scope_project',
        help = ("Target config option(s) in a project config file.")
    )

    group.add_argument('--global',
        action = 'store_true', dest = 'scope_global',
        help =  ("Target config option(s) in the global config file."),
    )

    group.add_argument('--file', metavar = "<FILE>",
        action = 'store', type = str, default = None, dest = 'scope_file',
        help = ("Target config option(s) in a specified config file.")
    )

def load_config_into_args(
        parser: argparse.ArgumentParser,
        args: argparse.Namespace,
        extra_state: typing.Dict[str, typing.Any],
        cli_arg_config_map: typing.Union[typing.Dict[str, str], None] = None,
        serialization_context: typing.Union[edq.util.serial.SerializationContext, None] = None,
        **kwargs: typing.Any,
        ) -> None:
    """
    Take in args from a parser that was passed to set_cli_args(),
    and get the tired configuration with the appropriate parameters, and attache it to args.

    Arguments that appear on the CLI as flags (e.g. `--foo bar`) can be copied over to the config options via `cli_arg_config_map`.
    The keys of `cli_arg_config_map` represent attributes in the CLI arguments (`args`),
    while the values represent the desired config name this argument should be set as.
    For example, a `cli_arg_config_map` of `{'foo': 'baz'}` will make the CLI argument `--foo bar`
    be equivalent to `--config baz=bar`.
    """

    if (cli_arg_config_map is None):
        cli_arg_config_map = {}

    for (cli_key, config_key) in cli_arg_config_map.items():
        value = getattr(args, cli_key, None)
        if (value is not None):
            getattr(args, edq.config.constants.CONFIG_OPTIONS_KEY).append(f"{config_key}={value}")

    default_values = {}
    for action in parser._actions:
        key = getattr(action, 'dest', None)
        if (key is None):
            continue

        default_values[str(key)] = getattr(action, 'default', None)

    config_info = edq.config.load.get_tiered_config(
        cli_arguments = args,
        cli_default_values = default_values,
        serialization_context = serialization_context,
    )
    setattr(args, "_config_info", config_info)
