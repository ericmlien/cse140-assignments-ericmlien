"""
Encrypt any unencrypted secrets present in configuration files.
"""

import argparse
import os

import edq.config.settings
import edq.config.util
import edq.util.crypto
import edq.util.serial

def run(args: argparse.Namespace) -> int:
    """ Run the target command and return the suggested exit status. """

    config_info = args._config_info

    paths = set()

    if (len(args.paths) > 0):
        paths |= set(args.paths)
    else:
        for load_results in args._config_info.sources.values():
            paths |= {result.path for result in load_results if (result.path is not None)}

    encryption_key = config_info.application_config.encryption_key
    config_class = type(config_info.application_config)
    serialization_context = edq.util.serial.SerializationContext(key = encryption_key)

    count = 0
    for path in sorted(paths):
        path = os.path.abspath(path)
        if (not os.path.exists(path)):
            continue

        file_config = config_class.from_path(path, context = serialization_context)

        to_write = {}
        for attr_name in dir(file_config):
            attr = getattr(file_config, attr_name, None)
            if (attr is None):
                continue

            if (not isinstance(attr, edq.util.crypto.Secret)):
                continue

            if (attr.is_encrypted()):
                continue

            to_write[attr_name] = attr.encrypt(encryption_key)
            count += 1

        if (len(to_write) > 0):
            print(f"Found {len(to_write)} unencrypted secret(s) in '{path}': {sorted(to_write.keys())}.")

        if ((len(to_write) > 0) and (not args.dry_run)):
            edq.config.util.update_options_in_config_file(path, to_write)

    if (count > 0):
        print(f"Encrypted {count} secret(s).")
    else:
        print("Found no unencrypted secrets.")

    return 0

def modify_parser(parser: argparse.ArgumentParser) -> None:
    """ Add this CLI's flags to the given parser. """

    group = parser.add_argument_group('encrypt options')

    group.add_argument('--dry-run', dest = 'dry_run',
        action = 'store_true',
        help = "Do not write any data, just state would would happen.",
    )

    group.add_argument('paths', metavar = 'PATHS',
        action = 'store', nargs = '*', type = str,
        help = "Optional paths to look for unencrypted secrets. If no paths are specified, all active config paths will be used.",
    )
