import argparse
import os
import typing

import edq.config.app
import edq.config.constants
import edq.config.settings
import edq.config.source
import edq.config.util
import edq.util.dirent
import edq.util.json
import edq.util.serial

class ConfigLoadResult(edq.util.serial.DictConverter):
    """ An instance of a config value being loaded from some config source. """

    def __init__(self,
            value: edq.util.serial.PODType,
            spec: edq.config.source.ConfigSourceSpec,
            path: typing.Union[str, None] = None,
            ) -> None:
        self.value: edq.util.serial.PODType = value
        """ The raw config value loaded. """

        self.spec: edq.config.source.ConfigSourceSpec = spec
        """ The config source spec that caused this item to be loaded. """

        self.path: typing.Union[str, None] = path
        """ If this result was loaded from a file, this is the path to that file. """

    def __repr__(self) -> str:
        if (self.path is not None):
            return f"<{self.spec.label} ({self.path})>"

        return f"<{self.spec.label}>"

class TieredConfigInfo(edq.util.serial.DictConverter):
    """ A class for storing config information read from a hierarchy of files and sources. """

    def __init__(self,
            raw_config: typing.Dict[str, edq.util.serial.PODType],
            sources: typing.Dict[str, typing.List[ConfigLoadResult]],
            application_config: typing.Union[edq.config.app.BaseApplicationConfig, None] = None,
            ) -> None:
        self.raw_config: typing.Dict[str, edq.util.serial.PODType] = raw_config
        """ The key-value config pairs after all overrides are processed. """

        self.sources: typing.Dict[str, typing.List[ConfigLoadResult]] = sources
        """
        A representation of every source/value loaded for each config key.
        As config values are loaded for a key, they are pushed (not appended) onto its dictionary value.
        The *first* value in the list represents the final loaded value (and should match the corresponding entry in self.raw_config).
        """

        if (application_config is None):
            application_config = edq.config.app.BaseApplicationConfig()

        self.application_config: edq.config.app.BaseApplicationConfig = application_config
        """ The config typed for the specific application. """

def get_tiered_config(
        cli_arguments: typing.Union[dict, argparse.Namespace, None] = None,
        cli_default_values: typing.Union[typing.Dict[str, typing.Any], None] = None,
        load_order: typing.Union[typing.List[edq.config.source.ConfigSourceSpec], None] = None,
        serialization_context: typing.Union[edq.util.serial.SerializationContext, None] = None,
        ) -> TieredConfigInfo:
    """
    Load all configuration options from files and command-line arguments.
    """

    if (cli_arguments is None):
        cli_arguments = {}

    if (cli_default_values is None):
        cli_default_values = {}

    if (load_order is None):
        load_order = edq.config.settings.get_load_order()

    raw_config: typing.Dict[str, edq.util.serial.PODType] = {}
    sources: typing.Dict[str, typing.List[ConfigLoadResult]] = {}

    # Ensure CLI arguments are always a dict,
    # even if provided as an argparse.Namespace.
    if (isinstance(cli_arguments, argparse.Namespace)):
        cli_arguments = vars(cli_arguments)

    # Load from each specified source.
    for spec in load_order:
        if (isinstance(spec, edq.config.source.CLIExplicitSpec)):
            for cli_config_option in cli_arguments.get(edq.config.constants.CONFIG_OPTIONS_KEY, []):
                (key, value) = edq.config.util.parse_string_config_option(cli_config_option)

                raw_config[key] = value

                if (key not in sources):
                    sources[key] = []

                sources[key].insert(0, ConfigLoadResult(value, spec))
        elif (isinstance(spec, edq.config.source.CLIImplicitSpec)):
            for (key, value) in cli_arguments.items():
                if (key in edq.config.constants.IGNORE_CLI_KEYS):
                    continue

                # Don't override existing values with default values.
                if ((key in sources) and (value == cli_default_values.get(key, None))):
                    continue

                raw_config[key] = value

                if (key not in sources):
                    sources[key] = []

                sources[key].insert(0, ConfigLoadResult(value, spec))
        elif (isinstance(spec, edq.config.source.CLIFileSpec)):
            config_paths = cli_arguments.get(edq.config.constants.CONFIG_PATHS_KEY, [])
            for path in config_paths:
                if (not os.path.exists(path)):
                    raise FileNotFoundError(f"Specified config file does not exist: '{path}'.")

                _load_config_file(path, raw_config, sources, spec)
        elif (isinstance(spec, edq.config.source.ENVSpec)):
            _load_env_variables(raw_config, sources, spec)
        elif (isinstance(spec, edq.config.source.GlobalSpec)):
            path = spec.resolve_path(override_path = cli_arguments.get(edq.config.constants.GLOBAL_CONFIG_KEY, None))
            _load_config_file(path, raw_config, sources, spec)
        elif (isinstance(spec, edq.config.source.AbstractPathSpec)):
            _load_config_file(spec.resolve_path(), raw_config, sources, spec)
        else:
            raise ValueError(f"Unknown config source spec: '{type(spec)}'.")

    if (serialization_context is None):
        serialization_context = edq.util.serial.SerializationContext()
    else:
        serialization_context = serialization_context.copy()

    raw_application_config = raw_config.copy()
    encryption_key = raw_application_config.get(
            edq.config.constants.CONFIG_ENCRYPTION_KEY,
            edq.config.settings.get_default_encryption_key())
    if (encryption_key is None):
        encryption_key = edq.config.settings.get_default_encryption_key()

    raw_application_config[edq.config.constants.CONFIG_ENCRYPTION_KEY] = str(encryption_key)
    serialization_context.key = str(encryption_key)

    application_config = edq.config.settings.get_application_config_class().from_dict(
        raw_application_config,
        context = serialization_context,
    )

    return TieredConfigInfo(
        raw_config,
        sources,
        application_config = application_config,
    )

def _load_config_file(
        config_path: str,
        config: typing.Dict[str, typing.Any],
        sources: typing.Dict[str, typing.List[ConfigLoadResult]],
        spec: edq.config.source.ConfigSourceSpec,
        ) -> None:
    """
    Loads config variables and the source from the given config JSON file.
    If the given config JSON file doesn't exit loads nothing.
    """

    if (not edq.util.dirent.exists(config_path)):
        return

    if (os.path.isdir(config_path)):
        raise IsADirectoryError(f"Failed to read config file, expected a file but got a directory at '{config_path}'.")

    config_path = os.path.abspath(config_path)
    for (key, value) in edq.util.json.load_path(config_path).items():
        key = edq.config.util.validate_config_key(key, value)

        config[key] = value

        if (key not in sources):
            sources[key] = []

        sources[key].insert(0, ConfigLoadResult(value, spec, config_path))

def _load_env_variables(
        config: typing.Dict[str, typing.Any],
        sources: typing.Dict[str, typing.List[ConfigLoadResult]],
        spec: edq.config.source.ConfigSourceSpec,
        ) -> None:
    """
    Load config from environmental variables.
    Any variable with a matching prefix will have the prefix removed and lower-cased.
    """

    prefix = edq.config.settings.get_env_prefix()
    for (key, value) in os.environ.items():
        if (not key.startswith(prefix)):
            continue

        key = key.removeprefix(prefix).lower()

        config[key] = value

        if (key not in sources):
            sources[key] = []

        sources[key].insert(0, ConfigLoadResult(value, spec))
