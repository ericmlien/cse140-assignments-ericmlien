import os
import typing

import edq.util.dirent
import edq.util.json

def update_options_in_config_file(path: str, config_to_write: typing.Dict[str, str]) -> None:
    """
    Write configs to the specified path.
    Create the path if it does not exist.
    Existing keys in the file will be overwritten with the new values.
    """

    config = {}
    if (edq.util.dirent.exists(path)):
        config = edq.util.json.load_path(path)

    config.update(config_to_write)

    edq.util.dirent.mkdir(os.path.dirname(path))
    edq.util.json.dump_path(config, path, indent = 4)

def remove_options_in_config_file(path: str, config_to_remove: typing.List[str]) -> None:
    """
    Remove configs from the specified path.
    Raises an exception if the given path doesn't exist.
    """

    config = edq.util.json.load_path(path)
    for config_option in config_to_remove:
        config.pop(config_option, None)

    edq.util.json.dump_path(config, path, indent = 4)

def parse_string_config_option(config_option: str) -> typing.Tuple[str, str]:
    """
    Parse and validate a configuration option string in the format of '<key>=<value>'.
    Returns the resulting config option as a key-value pair.
    """

    if ("=" not in config_option):
        raise ValueError(
            f"Invalid configuration option string '{config_option}'."
            + " Configuration options must be provided in the format '<key>=<value>'.")

    (key, value) = config_option.split('=', maxsplit = 1)
    key = validate_config_key(key, value)

    return key, value

def validate_config_key(config_key: str, config_value: str) -> str:
    """ Validate a configuration key and return its clean version. """

    key = config_key.strip()
    if (key == ''):
        raise ValueError(f"Found an empty configuration option key associated with the value '{config_value}'.")

    return key
