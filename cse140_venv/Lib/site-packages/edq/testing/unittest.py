import datetime
import difflib
import os
import typing
import unittest

import edq.util.dirent
import edq.util.json
import edq.util.reflection
import edq.util.serial
import edq.util.time

FORMAT_STR: str = "\n--- Expected ---\n%s\n--- Actual ---\n%s\n---\n"

DirentSpec = typing.Tuple[str, typing.Union[str, typing.Dict[str, edq.util.serial.PODType], typing.List['DirentSpec']]]  # pylint: disable=invalid-name
"""
A simple spec for a directory entry.
See create_directory_structure().
"""

class BaseTest(unittest.TestCase):
    """
    A base class for unit tests.
    """

    maxDiff = None
    """ Don't limit the size of diffs. """

    testing_timezone: typing.Union[datetime.timezone, None] = edq.util.time.UTC
    """ The timezone to use. """

    use_diff_output: bool = True
    """ Use diff-like comparisons. """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        edq.util.time.set_testing_local_timezone(cls.testing_timezone)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()

        edq.util.time.set_testing_local_timezone(None)

    def assertStringEqual(self, expected: str, actual: str, message: typing.Union[str, None] = None, strip: bool = False) -> None:  # pylint: disable=invalid-name
        """ Check that two strings are equal. """

        expected = str(expected)
        actual = str(actual)

        if (strip):
            expected = expected.strip()
            actual = actual.strip()

        if (actual != expected):
            if (message is None):
                message = self._format_comparison_message(expected, actual)

            self.fail(message)

    def assertJSONEqual(self, expected: typing.Any, actual: typing.Any, message: typing.Union[str, None] = None) -> None:  # pylint: disable=invalid-name
        """
        Like unittest.TestCase.assertEqual(),
        but uses expected default assertion message containing the full JSON representation of the arguments.
        """

        expected_json = edq.util.json.dumps(expected, indent = 4)
        actual_json = edq.util.json.dumps(actual, indent = 4)

        if (message is None):
            message = self._format_comparison_message(expected_json, actual_json)

        super().assertEqual(expected, actual, msg = message)

    def assertJSONDictEqual(self, expected: typing.Any, actual: typing.Any, message: typing.Union[str, None] = None) -> None:  # pylint: disable=invalid-name
        """
        Like unittest.TestCase.assertDictEqual(),
        but will try to convert each comparison argument to a dict if it is not already,
        and uses a default assertion message containing the full JSON representation of the arguments.
        """

        if (not isinstance(expected, dict)):
            if (isinstance(expected, edq.util.serial.DictConverter)):
                expected = expected.to_dict(edq.util.serial.SerializationContext())
            else:
                expected = vars(expected)

        if (not isinstance(actual, dict)):
            if (isinstance(actual, edq.util.serial.DictConverter)):
                actual = actual.to_dict(edq.util.serial.SerializationContext())
            else:
                actual = vars(actual)

        expected_json = edq.util.json.dumps(expected, indent = 4)
        actual_json = edq.util.json.dumps(actual, indent = 4)

        if (message is None):
            message = self._format_comparison_message(expected_json, actual_json)

        super().assertDictEqual(expected, actual, msg = message)

    def assertJSONListEqual(self,  # pylint: disable=invalid-name
            expected: typing.List[typing.Any],
            actual: typing.List[typing.Any],
            message: typing.Union[str, None] = None,
            ) -> None:
        """
        Call assertDictEqual(), but supply a default message containing the full JSON representation of the arguments.
        """

        expected_json = edq.util.json.dumps(expected, indent = 4)
        actual_json = edq.util.json.dumps(actual, indent = 4)

        if (message is None):
            message = self._format_comparison_message(expected_json, actual_json)

        super().assertListEqual(expected, actual, msg = message)

    def assertFileHashEqual(self, expected: str, actual: str) -> None:  # pylint: disable=invalid-name
        """
        Assert that the hash of two files matches.
        Will fail if either path does not exist.
        """

        if (not edq.util.dirent.exists(expected)):
            self.fail(f"File does not exist: '{expected}'.")

        if (not edq.util.dirent.exists(actual)):
            self.fail(f"File does not exist: '{actual}'.")

        expected_hash = edq.util.dirent.hash_file(expected)
        actual_hash = edq.util.dirent.hash_file(actual)

        self.assertEqual(expected_hash, actual_hash, msg = f"Hash mismatch: '{expected}' ({expected_hash}) vs '{actual}' ({actual_hash}).")

    def format_error_string(self, ex: typing.Union[BaseException, None]) -> str:
        """
        Format an error string from an exception so it can be checked for testing.
        The type of the error will be included,
        and any nested errors will be joined together.
        """

        parts = []

        while (ex is not None):
            type_name = edq.util.reflection.get_qualified_name(ex)
            message = str(ex)

            parts.append(f"{type_name}: {message}")

            ex = ex.__cause__

        return "; ".join(parts)

    def _format_comparison_message(self, expected: str, actual: str) -> str:
        """ Create a message string comparing the two given strings. """

        message = FORMAT_STR % (expected, actual)

        if (not self.use_diff_output):
            return message

        expected_lines = expected.splitlines(keepends = True)
        actual_lines = actual.splitlines(keepends = True)

        lines = list(difflib.unified_diff(expected_lines, actual_lines, fromfile = 'expected', tofile = 'actual'))
        message += "\n--- Diff ---\n" + ''.join(lines) + "\n------------"

        return message

def create_directory_structure(spec: typing.List[DirentSpec], base_dir: str) -> None:
    """
    Create a directory strucutre from a simple definition.
    The definition represents a list of direents.
    Each dirent is a tuple with the name of a dirent and the contents of the dirent.
    The contents can be:
        1) a list if dirents (indicating that this dirent is a directory),
        2) a dict (indicating that this dirent is a JSON file),
        or 3) a string (indicating that this dirent is a text file).
    """

    for (name, contents) in spec:
        path = os.path.join(base_dir, name)

        if (isinstance(contents, str)):
            edq.util.dirent.write_file(path, contents)
        elif (isinstance(contents, dict)):
            edq.util.json.dump_path(contents, path, indent = 4)
        elif (isinstance(contents, list)):
            edq.util.dirent.mkdir(path)
            create_directory_structure(contents, path)
        else:
            raise ValueError(f"Unknown dirent content type ('{type(contents)}') at path: '{path}'.")
