import typing

import edq.config.app
import edq.config.common
import edq.config.constants
import edq.config.source
import edq.util.serial

def get_application_config_class() -> typing.Type[edq.config.app.BaseApplicationConfig]:
    """ Get the application config class. """

    return typing.cast(typing.Type[edq.config.app.BaseApplicationConfig], edq.config.common._application_config_class)

def set_application_config_class(config_class: typing.Union[typing.Type[edq.config.app.BaseApplicationConfig], None] = None) -> None:
    """ Set the application config class. """

    if (config_class is None):
        config_class = edq.config.common._DEFAULT_APPLICATION_CONFIG_CLASS  # type: ignore[assignment]

    edq.config.common._application_config_class = config_class  # type: ignore[assignment]

def get_config_filename() -> str:
    """ Get the config filename. """

    return edq.config.common._config_filename

def set_config_filename(filename: typing.Union[str, None] = None) -> None:
    """ Set the config filename. """

    if (filename is None):
        filename = edq.config.common._DEFAULT_CONFIG_FILENAME

    edq.config.common._config_filename = filename

def get_default_encryption_key() -> str:
    """ Get the default encryption key. """

    return edq.config.common._default_encryption_key

def set_default_encryption_key(encryption_key: typing.Union[str, None] = None) -> None:
    """ Set the default encryption key. """

    if (encryption_key is None):
        encryption_key = edq.config.common._DEFAULT_DEFAULT_ENCRYPTION_KEY

    edq.config.common._default_encryption_key = encryption_key

def get_env_prefix() -> str:
    """ Get the environmental variable prefix. """

    return edq.config.common._env_prefix

def set_env_prefix(prefix: typing.Union[str, None] = None) -> None:
    """ Set the environmental variable prefix. """

    if (prefix is None):
        prefix = edq.config.common._DEFAULT_ENV_PREFIX

    edq.config.common._env_prefix = prefix

def get_global_dir() -> str:
    """ Get the global config dir. """

    return edq.config.common._global_dir

def set_global_dir(global_dir: typing.Union[str, None] = None) -> None:
    """ Set the global config dir. """

    if (global_dir is None):
        global_dir = edq.config.common._DEFAULT_GLOBAL_DIR

    edq.config.common._global_dir = global_dir

def get_load_order() -> typing.List[edq.config.source.ConfigSourceSpec]:
    """ Get the order to load config sources. """

    return typing.cast(typing.List[edq.config.source.ConfigSourceSpec], edq.config.common._load_order)

def set_load_order(load_order: typing.Union[typing.List[edq.config.source.ConfigSourceSpec], None]) -> None:
    """ Set the order to load config sources. """

    if (load_order is None):
        load_order = typing.cast(typing.List[edq.config.source.ConfigSourceSpec], edq.config.common._DEFAULT_LOAD_ORDER.copy())

    edq.config.common._load_order = load_order  # type: ignore[assignment]
