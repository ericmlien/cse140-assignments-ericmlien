"""
List the current configuration options.
"""

import argparse

import edq.config.source

CONFIG_FIELD_SEPARATOR: str = "\t"

def run(args: argparse.Namespace) -> int:
    """ Run the target command and return the suggested exit status. """

    config_info = args._config_info

    rows = []
    for (key, value) in config_info.raw_config.items():
        if ((not args.include_cli) and isinstance(args._config_info.sources[key][0].spec, edq.config.source.CLIImplicitSpec)):
            continue

        row = [key, str(value)]
        if (args.show_origin):
            row.append(str(config_info.sources[key][-1]))

        rows.append(CONFIG_FIELD_SEPARATOR.join(row))

    rows.sort()

    if (not args.skip_header):
        header = ["Key", "Value"]
        if (args.show_origin):
            header.append("Origin")

        rows.insert(0, (CONFIG_FIELD_SEPARATOR.join(header)))

    print("\n".join(rows))
    return 0

def modify_parser(parser: argparse.ArgumentParser) -> None:
    """ Add this CLI's flags to the given parser. """

    group = parser.add_argument_group('list options')

    group.add_argument("--include-cli", dest = 'include_cli',
        action = 'store_true',
        help = "Include implicit CLI config values (values defined directly on the CLI but not with `--config`).",
    )

    group.add_argument("--show-origin", dest = 'show_origin',
        action = 'store_true',
        help = "Display where each configuration's value was obtained from.",
    )

    group.add_argument("--skip-header", dest = 'skip_header',
        action = 'store_true',
        help = 'Skip headers when displaying configs.',
    )
