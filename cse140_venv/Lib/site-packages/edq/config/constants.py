import typing

CONFIG_PATHS_KEY: str = 'config_paths'
GLOBAL_CONFIG_KEY: str = 'global_config_path'
CONFIG_OPTIONS_KEY: str = 'configs'
CONFIG_ENCRYPTION_KEY: str = 'encryption_key'

IGNORE_CLI_KEYS: typing.Set[str] = {
    CONFIG_PATHS_KEY,
    GLOBAL_CONFIG_KEY,
    CONFIG_OPTIONS_KEY,
}

DEFAULT_INDENT: int = 4
