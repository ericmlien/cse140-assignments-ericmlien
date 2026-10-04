import os
import typing

import edq.config.app
import edq.config.constants
import edq.config.load
import edq.config.settings
import edq.config.testing
import edq.testing.unittest
import edq.util.dirent
import edq.util.serial

class TestLoadConfig(edq.testing.unittest.BaseTest):
    """ Test basic operations of loading configs. """

    def tearDown(self) -> None:
        edq.config.settings.set_config_filename()

        # Clear env variables.
        edq.config.testing.clear_env()

    def test_get_tiered_config_base(self) -> None:
        """
        Test that configuration files are loaded correctly from the file system with the expected tier.
        """

        temp_dir = edq.util.dirent.get_temp_dir(prefix = "edq-test-config-get-tiered-config-")

        # Global config will always be set to `<base dir>/global.json` if not set in the CLI arguments.

        # Change the config filename to reduce the chance of collision.
        edq.config.settings.set_config_filename('edq-testing.json')

        # Create a variable for each config source spec to make it easier for testing.
        (spec_global, spec_project, spec_env, spec_cli_file, spec_cli_implicit, spec_cli_explicit) = edq.config.settings.get_load_order()

        # [(test case label, directory structure, cli arguments, env variables, expected raw config, expected sources, error substring), ...]
        test_cases: typing.List[typing.Tuple[
            str,
            typing.List[edq.testing.unittest.DirentSpec],
            typing.Dict[str, edq.util.serial.PODType],
            typing.Dict[str, str],
            typing.Dict[str, edq.util.serial.PODType],
            typing.Dict[str, typing.List[edq.config.load.ConfigLoadResult]],
            typing.Union[str, None],
        ]] = [
            (
                'Empty',
                [],
                {},
                {},
                {},
                {},
                None,
            ),

            (
                'Project - Base',
                [
                    ('edq-testing.json', {
                        'user': 'user@test.edulinq.org',
                    }),
                ],
                {},
                {},
                {
                    'user': 'user@test.edulinq.org',
                },
                {
                    'user': [
                        edq.config.load.ConfigLoadResult('user@test.edulinq.org', spec_project, 'edq-testing.json'),
                    ],
                },
                None,
            ),

            (
                'Global - Base',
                [
                    ('global.json', {
                        'user': 'user@test.edulinq.org',
                    }),
                ],
                {},
                {},
                {
                    'user': 'user@test.edulinq.org',
                },
                {
                    'user': [
                        edq.config.load.ConfigLoadResult('user@test.edulinq.org', spec_global, 'global.json'),
                    ],
                },
                None,
            ),

            (
                'ENV - Base',
                [],
                {},
                {
                    'EDQ__USER': 'user@test.edulinq.org',
                },
                {
                    'user': 'user@test.edulinq.org',
                },
                {
                    'user': [
                        edq.config.load.ConfigLoadResult('user@test.edulinq.org', spec_env),
                    ],
                },
                None,
            ),

            (
                'CLI File - Base',
                [
                    ('foo.json', {
                        'user': 'user@test.edulinq.org',
                    }),
                ],
                {
                    edq.config.constants.CONFIG_PATHS_KEY: ['foo.json'],
                },
                {},
                {
                    'user': 'user@test.edulinq.org',
                },
                {
                    'user': [
                        edq.config.load.ConfigLoadResult('user@test.edulinq.org', spec_cli_file, 'foo.json'),
                    ],
                },
                None,
            ),

            (
                'CLI Explicit - Base',
                [],
                {
                    edq.config.constants.CONFIG_OPTIONS_KEY: [
                        "user=user@test.edulinq.org",
                    ],
                },
                {},
                {
                    'user': 'user@test.edulinq.org',
                },
                {
                    'user': [
                        edq.config.load.ConfigLoadResult('user@test.edulinq.org', spec_cli_explicit),
                    ],
                },
                None,
            ),

            (
                'CLI Implicit - Base',
                [],
                {
                    'user': 'user@test.edulinq.org',
                },
                {},
                {
                    'user': 'user@test.edulinq.org',
                },
                {
                    'user': [
                        edq.config.load.ConfigLoadResult('user@test.edulinq.org', spec_cli_implicit),
                    ],
                },
                None,
            ),

            (
                'CLI File - Multiple',
                [
                    ('foo.json', {
                        'a': 'A - foo',
                        'b': 'B - foo',
                    }),
                    ('bar.json', {
                        'b': 'B - bar',
                        'c': 'C - bar',
                    }),
                ],
                {
                    edq.config.constants.CONFIG_PATHS_KEY: [
                        'foo.json',
                        'bar.json',
                    ],
                },
                {},
                {
                    'a': 'A - foo',
                    'b': 'B - bar',
                    'c': 'C - bar',
                },
                {
                    'a': [
                        edq.config.load.ConfigLoadResult('A - foo', spec_cli_file, 'foo.json'),
                    ],
                    'b': [
                        edq.config.load.ConfigLoadResult('B - bar', spec_cli_file, 'bar.json'),
                        edq.config.load.ConfigLoadResult('B - foo', spec_cli_file, 'foo.json'),
                    ],
                    'c': [
                        edq.config.load.ConfigLoadResult('C - bar', spec_cli_file, 'bar.json'),
                    ],
                },
                None,
            ),

            (
                'ENV - Casing',
                [],
                {},
                {
                    'EDQ__uSeR': 'user@test.edulinq.org',
                },
                {
                    'user': 'user@test.edulinq.org',
                },
                {
                    'user': [
                        edq.config.load.ConfigLoadResult('user@test.edulinq.org', spec_env),
                    ],
                },
                None,
            ),

            (
                'ENV - Bad Prefix',
                [],
                {},
                {
                    'ZZZ__USER': 'user@test.edulinq.org',
                },
                {},
                {},
                None,
            ),

            (
                'Many Sources',
                [
                    ('edq-testing.json', {
                        'key': 'project',
                    }),
                    ('global.json', {
                        'key': 'global',
                    }),
                    ('foo.json', {
                        'key': 'cli file',
                    }),
                ],
                {
                    edq.config.constants.CONFIG_PATHS_KEY: [
                        'foo.json',
                    ],
                    edq.config.constants.CONFIG_OPTIONS_KEY: [
                        "key=cli",
                    ],
                },
                {
                    'EDQ__key': 'env',
                },
                {
                    'key': 'cli',
                },
                {
                    'key': [
                        edq.config.load.ConfigLoadResult('cli', spec_cli_explicit),
                        edq.config.load.ConfigLoadResult('cli file', spec_cli_file, 'foo.json'),
                        edq.config.load.ConfigLoadResult('env', spec_env),
                        edq.config.load.ConfigLoadResult('project', spec_project, 'edq-testing.json'),
                        edq.config.load.ConfigLoadResult('global', spec_global, 'global.json'),
                    ],
                },
                None,
            ),

            (
                'Error - Malformed JSON',
                [
                    ('edq-testing.json', 'Not JSON.'),
                ],
                {},
                {},
                {},
                {},
                'Failed to read JSON file',
            ),

            (
                'Error - Missing File',
                [],
                {
                    edq.config.constants.CONFIG_PATHS_KEY: ['foo.json'],
                },
                {},
                {},
                {},
                'file does not exist',
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            (test_case_label, directory_structure, cli_arguments, env_variables, expected_raw_config, expected_sources, error_substring) = test_case

            with self.subTest(msg = f"Case {i} ('{test_case_label}'):"):
                # Each test gets its own directory.
                base_dir = os.path.join(temp_dir, f"{i:03d}")
                edq.util.dirent.mkdir(base_dir)

                # Create the directory structure.
                edq.testing.unittest.create_directory_structure(directory_structure, base_dir)

                # Set environmental variables.
                edq.config.testing.clear_env()
                os.environ.update(env_variables)

                # Set the global config.
                if (edq.config.constants.GLOBAL_CONFIG_KEY not in cli_arguments):
                    cli_arguments[edq.config.constants.GLOBAL_CONFIG_KEY] = os.path.join(base_dir, 'global.json')

                # Update any relative load result paths with the test's directory.
                for load_results in expected_sources.values():
                    for load_result in load_results:
                        if (load_result.path is None):
                            continue

                        if (not os.path.isabs(load_result.path)):
                            load_result.path = os.path.join(base_dir, load_result.path)

                # Create the expected output.
                expected_config_info = edq.config.load.TieredConfigInfo(
                    raw_config = expected_raw_config,
                    sources = expected_sources,
                    application_config = edq.config.app.BaseApplicationConfig.from_dict(expected_raw_config),
                )

                previous_work_directory = os.getcwd()
                os.chdir(base_dir)

                try:
                    actual_config_info = edq.config.load.get_tiered_config(cli_arguments = cli_arguments,)
                except Exception as ex:
                    error_string = self.format_error_string(ex)

                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue
                finally:
                    os.chdir(previous_work_directory)

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

                # Normalize some keys from the application config.
                for normalize_key in edq.config.constants.IGNORE_CLI_KEYS:
                    setattr(actual_config_info.application_config, normalize_key, None)
                    setattr(expected_config_info.application_config, normalize_key, None)

                self.assertJSONEqual(expected_config_info, actual_config_info)
