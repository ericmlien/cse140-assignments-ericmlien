import os
import typing

import edq.config.constants
import edq.config.settings
import edq.config.testing
import edq.config.util
import edq.testing.unittest
import edq.util.json

class TestConfigUtils(edq.testing.unittest.BaseTest):
    """ Test configuration utils. """

    def test_update_config_base(self) -> None:
        """
        Test that the given config is updated correctly and paths are created correctly.
        """

        temp_dir = edq.util.dirent.get_temp_dir(prefix = "edq-test_update_config_base")

        # [(directory structure, rel path, config to write, expected result, error substring), ...]
        test_cases: typing.List[typing.Tuple[
            typing.List[edq.testing.unittest.DirentSpec],
            str,
            typing.Dict[str, typing.Any],
            typing.Dict[str, typing.Any],
            typing.Union[str, None],
        ]] = [
            # Non-exisiting Path
            (
                [],
                'non-exisiting.json',
                {
                    'user': 'user@test.edulinq.org',
                },
                {
                    'user': 'user@test.edulinq.org',
                },
                None,
            ),

            # Directory Path
            (
                [
                    ('some-dir', []),
                ],
                'some-dir',
                {},
                {},
                "Cannot open JSON file, expected a file but got a directory",
            ),

            # Empty Config
            (
                [
                    ('config.json', {}),
                ],
                'config.json',
                {
                    'user': 'user@test.edulinq.org',
                },
                {
                    'user': 'user@test.edulinq.org',
                },
                None,
            ),

            # Non-empty Config
            (
                [
                    ('config.json', {
                        'user': 'user@test.edulinq.org',
                    }),
                ],
                'config.json',
                {
                    'pass': 'password1234',
                },
                {
                    'user': 'user@test.edulinq.org',
                    'pass': 'password1234',
                },
                None,
            ),

            # Non-empty Config (Overwrite)
            (
                [
                    ('config.json', {
                        'user': 'alice@test.edulinq.org',
                    }),
                ],
                'config.json',
                {
                    'user': 'user@test.edulinq.org',
                },
                {
                    'user': 'user@test.edulinq.org',
                },
                None,
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            directory_structure, relpath, config_to_write, expected, error_substring = test_case

            with self.subTest(msg = f"Case {i}"):
                base_dir = os.path.join(temp_dir, f"{i:03d}")
                edq.util.dirent.mkdir(base_dir)

                path = os.path.join(base_dir, relpath)

                edq.testing.unittest.create_directory_structure(directory_structure, base_dir)

                previous_work_directory = os.getcwd()
                os.chdir(base_dir)

                try:
                    edq.config.util.update_options_in_config_file(path, config_to_write)
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

                actual = edq.util.json.load_path(path)
                self.assertJSONDictEqual(expected, actual)

    def test_remove_config_option_base(self) -> None:
        """
        Test that the given config option(s) are removed correctly.
        """

        temp_dir = edq.util.dirent.get_temp_dir(prefix = "edq-test_remove_config_option_base")

        # [(directory structure, rel path, config to remove, expected result, error substring), ...]
        test_cases: typing.List[typing.Tuple[
            typing.List[edq.testing.unittest.DirentSpec],
            str,
            typing.List[str],
            typing.Dict[str, typing.Any],
            typing.Union[str, None],
        ]] = [
            # Non-exisiting Path
            (
                [],
                'non-exisiting.json',
                [],
                {},
                "FileNotFoundError",
            ),

            # Directory Path
            (
                [
                    ('some-dir', []),
                ],
                'some-dir',
                [],
                {},
                "Cannot open JSON file, expected a file but got a directory",
            ),

            # Remove No Options
            (
                [
                    ('config.json', {
                        'user': 'user@test.edulinq.org',
                    }),
                ],
                'config.json',
                [
                    'pass',
                ],
                {
                    'user': 'user@test.edulinq.org',
                },
                None,
            ),

            # Empty Config
            (
                [
                    ('config.json', {}),
                ],
                'config.json',
                [
                    'user',
                ],
                {},
                None,
            ),

            # Non-empty Config (Remove Single Option)
            (
                [
                    ('config.json', {
                        'user': 'user@test.edulinq.org',
                        'pass': 'password1234',
                    }),
                ],
                'config.json',
                [
                    'user',
                ],
                {
                    'pass': 'password1234',
                },
                None,
            ),

            # Non-empty Config (Remove Multiple Options)
            (
                [
                    ('config.json', {
                        'user': 'user@test.edulinq.org',
                        'pass': 'password1234',
                    }),
                ],
                'config.json',
                [
                    'user',
                    'pass',
                ],
                {},
                None,
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            directory_structure, relpath, config_to_remove, expected, error_substring = test_case

            with self.subTest(msg = f"Case {i}"):
                base_dir = os.path.join(temp_dir, f"{i:03d}")
                edq.util.dirent.mkdir(base_dir)

                path = os.path.join(base_dir, relpath)

                edq.testing.unittest.create_directory_structure(directory_structure, base_dir)

                previous_work_directory = os.getcwd()
                os.chdir(base_dir)

                try:
                    edq.config.util.remove_options_in_config_file(path, config_to_remove)
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

                actual = edq.util.json.load_path(path)
                self.assertJSONDictEqual(expected, actual)
