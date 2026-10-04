import os
import typing

import edq.testing.unittest
import edq.util.dirent
import edq.util.gzip
import edq.util.json
import edq.util.reflection

class TestJSON(edq.testing.unittest.BaseTest):
    """ Test JSON utils. """

    def test_loading_dumping_base(self) -> None:
        """
        Test the family of JSON loading and dumping functions.
        """

        # [(string, dict, strict?, error_substring), ...]
        test_cases: typing.List[typing.Tuple[
            str,
            typing.Dict[str, typing.Any],
            bool,
            typing.Union[str, None],
        ]] = [
            # Base
            (
                '{"a": 1}',
                {"a": 1},
                False,
                None,
            ),

            # Trivial - Strict
            (
                '{"a": 1}',
                {"a": 1},
                True,
                None,
            ),

            # JSON5
            (
                '{"a": 1,}',
                {"a": 1},
                False,
                None,
            ),

            # JSON5 - Strict
            (
                '{"a": 1,}',
                {"a": 1},
                True,
                'JSONDecodeError',
            ),
        ]

        # [(function, name), ...]
        test_methods = [
            (self._subtest_loads_dumps, 'subtest_loads_dumps'),
            (self._subtest_load_dump, 'subtest_load_dump'),
            (self._subtest_load_dump_path, 'subtest_load_dump_path'),
            (self._subtest_load_gzip, 'subtest_load_gzip'),
            (self._subtest_load_dump_path_gzip, 'subtest_load_dump_path_gzip'),
        ]

        for (test_method, test_method_name) in test_methods:
            for (i, test_case) in enumerate(test_cases):
                (text_content, dict_content, strict, error_substring) = test_case

                with self.subTest(msg = f"Subtest {test_method_name}, Case {i} ('{text_content}'):"):
                    try:
                        test_method(text_content, dict_content, strict)
                    except AssertionError:
                        # The subttest failed an assertion.
                        raise
                    except Exception as ex:
                        error_string = self.format_error_string(ex)
                        if (error_substring is None):
                            self.fail(f"Unexpected error: '{error_string}'.")

                        self.assertIn(error_substring, error_string, 'Error is not as expected.')

                        continue

                    if (error_substring is not None):
                        self.fail(f"Did not get expected error: '{error_substring}'.")

    def _subtest_loads_dumps(self, text_content: str, dict_content: typing.Dict[str, typing.Any], strict: bool) -> None:
        actual_dict = edq.util.json.loads(text_content, strict = strict)
        actual_text = edq.util.json.dumps(dict_content)
        double_conversion_text = edq.util.json.dumps(actual_dict)

        self.assertDictEqual(dict_content, actual_dict)
        self.assertEqual(actual_text, double_conversion_text)

    def _subtest_load_dump(self, text_content: str, dict_content: typing.Dict[str, typing.Any], strict: bool) -> None:
        temp_dir = edq.util.dirent.get_temp_dir(prefix = 'edq_test_json_')

        path_text = os.path.join(temp_dir, 'test-text.json')
        path_dict = os.path.join(temp_dir, 'test-dict.json')

        edq.util.dirent.write_file(path_text, text_content)

        with open(path_text, 'r', encoding = edq.util.dirent.DEFAULT_ENCODING) as file:
            text_load = edq.util.json.load(file, strict = strict)

        with open(path_dict, 'w', encoding = edq.util.dirent.DEFAULT_ENCODING) as file:
            edq.util.json.dump(dict_content, file)

        with open(path_dict, 'r', encoding = edq.util.dirent.DEFAULT_ENCODING) as file:
            dict_load = edq.util.json.load(file, strict = strict)

        self.assertDictEqual(dict_content, text_load)
        self.assertDictEqual(dict_load, text_load)

    def _subtest_load_gzip(self, text_content: str, dict_content: typing.Dict[str, typing.Any], strict: bool) -> None:
        temp_dir = edq.util.dirent.get_temp_dir(prefix = 'edq_test_json_gzip_')

        path = os.path.join(temp_dir, 'test.json.gz')
        edq.util.gzip.compress_to_path(text_content.encode(edq.util.dirent.DEFAULT_ENCODING), path)

        with open(path, 'rb') as file:
            load_data = edq.util.json.load(file, strict = strict, gzipped = True)

        self.assertDictEqual(dict_content, load_data)

    def _subtest_load_dump_path(self, text_content: str, dict_content: typing.Dict[str, typing.Any], strict: bool) -> None:
        temp_dir = edq.util.dirent.get_temp_dir(prefix = 'edq_test_json_path_')

        path_text = os.path.join(temp_dir, 'test-text.json')
        path_dict = os.path.join(temp_dir, 'test-dict.json')

        edq.util.dirent.write_file(path_text, text_content)
        text_load = edq.util.json.load_path(path_text, strict = strict)

        edq.util.json.dump_path(dict_content, path_dict)
        dict_load = edq.util.json.load_path(path_dict, strict = strict)

        self.assertDictEqual(dict_content, text_load)
        self.assertDictEqual(dict_load, text_load)

    def _subtest_load_dump_path_gzip(self, text_content: str, dict_content: typing.Dict[str, typing.Any], strict: bool) -> None:
        # Trigger error on parsing tests.
        edq.util.json.loads(text_content, strict = strict)

        temp_dir = edq.util.dirent.get_temp_dir(prefix = 'edq_test_json_path_gzip_', rm = False)

        path_ext = os.path.join(temp_dir, 'test.json.gz')
        path_noext = os.path.join(temp_dir, 'test')

        edq.util.json.dump_path(dict_content, path_ext)
        edq.util.json.dump_path(dict_content, path_noext, gzipped = True)

        load_ext = edq.util.json.load_path(path_ext, strict = strict)
        load_noext = edq.util.json.load_path(path_noext, strict = strict, gzipped = True)

        self.assertDictEqual(dict_content, load_ext)
        self.assertDictEqual(dict_content, load_noext)
