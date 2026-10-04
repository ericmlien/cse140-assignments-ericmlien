import enum
import os
import typing

import edq.config.app
import edq.config.settings
import edq.testing.cli
import edq.testing.unittest
import edq.util.crypto
import edq.util.json

class TestEnumStr(enum.Enum):
    """ A test enum that only has strings. """

    FIRST = 'a'
    SECOND = 'b'

class TestApplicationConfig(edq.config.app.BaseApplicationConfig):
    """ A test application config. """

    serialization_omit_none = True

    def __init__(self,
            user: typing.Union[str, None] = None,
            token: typing.Union[edq.util.crypto.Secret, None] = None,
            number: typing.Union[int, None] = None,
            enum_value: typing.Union[TestEnumStr, None] = None,
            **kwargs: typing.Any) -> None:
        super().__init__(**kwargs)

        self.user: typing.Union[str, None] = user
        self.token: typing.Union[edq.util.crypto.Secret, None] = token
        self.number: typing.Union[int, None] = number
        self.enum_value: typing.Union[TestEnumStr, None] = enum_value

def clear_env() -> None:
    """ Clear out any EDQ-looking environment variables. """

    for key in os.environ.keys():
        if (key.startswith(edq.config.settings.get_env_prefix())):
            os.environ.pop(key, None)

def verify_cli_test_config_content(
        test: edq.testing.unittest.BaseTest,
        test_info: edq.testing.cli.CLITestInfo,
        ) -> None:
    """ Verify the contents of a config file created by a CLI test. """

    path = os.path.join(test_info.work_dir, *test_info.extra_options["path"].split('/'))

    data_actual = edq.util.json.load_path(path)
    data_expected = test_info.extra_options["data"]

    test.assertJSONDictEqual(data_expected, data_actual)

def set_testing_application_config_class(
        test: edq.testing.unittest.BaseTest,
        test_info: edq.testing.cli.CLITestInfo,
        ) -> None:
    """ Set the application config class to a more varied testing one. """

    edq.config.settings.set_application_config_class(TestApplicationConfig)

def clear_testing_application_config_class(
        test: edq.testing.unittest.BaseTest,
        test_info: edq.testing.cli.CLITestInfo,
        ) -> None:
    """ Clear the application config class. """

    edq.config.settings.set_application_config_class()
