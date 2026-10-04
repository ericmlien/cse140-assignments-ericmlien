import enum

import edq.testing.unittest
import edq.util.enum

# Ideally this would be enum.StrEnum, but that was introduced in Python 3.11.
class _TestEnumStr(enum.Enum):
    """ A test enum that only has strings. """

    FIRST = 'a'
    SECOND = 'b'

class _TestEnumInt(enum.IntEnum):
    """ A test enum that only has ints. """

    FIRST = 1
    SECOND = 2

class _TestEnumMix(enum.Enum):
    """ A test enum that has mixed values. """

    FIRST = 'a'
    SECOND = 2

class TestEnum(edq.testing.unittest.BaseTest):
    """ Test enum utils. """

    def test_has_value_base(self) -> None:
        """
        Test checking if an enum has a specific value.
        """

        # [(enum class, value, expected), ...]
        test_cases = [
            # String Enum
            (
                _TestEnumStr,
                'a',
                True,
            ),
            (
                _TestEnumStr,
                'b',
                True,
            ),
            (
                _TestEnumStr,
                _TestEnumStr.FIRST,
                True,
            ),
            (
                _TestEnumStr,
                _TestEnumStr.SECOND,
                True,
            ),
            (
                _TestEnumStr,
                'ZZZ',
                False,
            ),
            (
                _TestEnumStr,
                _TestEnumInt.FIRST,
                False,
            ),

            # Int Enum
            (
                _TestEnumInt,
                1,
                True,
            ),
            (
                _TestEnumInt,
                2,
                True,
            ),
            (
                _TestEnumInt,
                _TestEnumInt.FIRST,
                True,
            ),
            (
                _TestEnumInt,
                _TestEnumInt.SECOND,
                True,
            ),
            (
                _TestEnumInt,
                '1',
                False,
            ),
            (
                _TestEnumInt,
                'a',
                False,
            ),
            (
                _TestEnumInt,
                _TestEnumStr.FIRST,
                False,
            ),

            # Mixed Enum
            (
                _TestEnumMix,
                'a',
                True,
            ),
            (
                _TestEnumMix,
                2,
                True,
            ),
            (
                _TestEnumMix,
                _TestEnumMix.FIRST,
                True,
            ),
            (
                _TestEnumMix,
                _TestEnumMix.SECOND,
                True,
            ),
            (
                _TestEnumMix,
                3,
                False,
            ),
            (
                _TestEnumMix,
                '2',
                False,
            ),
            (
                _TestEnumMix,
                _TestEnumStr.FIRST,
                False,
            ),
            (
                _TestEnumMix,
                _TestEnumInt.SECOND,
                False,
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            (enum_class, value, expected) = test_case

            with self.subTest(msg = f"Case {i} ({enum_class}, '{value}')"):
                actual = edq.util.enum.has_value(enum_class, value)
                self.assertEqual(expected, actual)
