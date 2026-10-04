import os
import typing

import edq.config.app
import edq.config.constants
import edq.config.load
import edq.config.testing
import edq.testing.unittest
import edq.util.crypto
import edq.util.dirent
import edq.util.json
import edq.util.serial

class TestApplicationConfig(edq.testing.unittest.BaseTest):
    """ Test basic operations on configs. """

    def tearDown(self) -> None:
        edq.config.settings.set_application_config_class()
        os.environ.pop('EDQ__ENCRYPTION_KEY', None)

    def test_application_config_base(self) -> None:
        """
        Test loading config into an application config.
        """

        edq.config.settings.set_application_config_class(edq.config.testing.TestApplicationConfig)

        temp_dir = edq.util.dirent.get_temp_dir(prefix = "edq-test_application_config_base")

        # Use a fixed key.
        os.environ['EDQ__ENCRYPTION_KEY'] = 'key'
        serialization_context = edq.util.serial.SerializationContext(key = 'key')

        # [(application config, dict POD config), ...]
        test_cases: typing.List[typing.Tuple[
            edq.config.app.BaseApplicationConfig,
            typing.Dict[str, typing.Any],
        ]] = [
            # Base
            (
                edq.config.testing.TestApplicationConfig(user = 'alice'),
                {
                    'user': 'alice',
                },
            ),

            # Numeric
            (
                edq.config.testing.TestApplicationConfig(number = 4),
                {
                    'number': 4,
                },
            ),

            # Enum
            (
                edq.config.testing.TestApplicationConfig(enum_value = edq.config.testing.TestEnumStr.FIRST),
                {
                    'enum_value': 'a',
                },
            ),

            # Secret - No Encryption
            (
                edq.config.testing.TestApplicationConfig(token = edq.util.crypto.Secret('secret')),
                {
                    'token': 'secret',
                },
            ),

            # Secret - Encryption
            (
                edq.config.testing.TestApplicationConfig(
                    token = edq.util.crypto.Secret('secret', iv_b64 = 'UldcITh761FJcMRThJpkag==', salt_b64 = 'niOb2keWPoSwR1MlgWHayQ=='),
                ),
                {
                    'token': '__edq_secret__::AES256v1::UldcITh761FJcMRThJpkag==::niOb2keWPoSwR1MlgWHayQ==::sN3Tl4WCA6X+xszcnTO+9Q==',
                },
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            expected_application_config, expected_dict_config = test_case

            with self.subTest(msg = f"Case {i}"):
                base_dir = os.path.join(temp_dir, f"{i:03d}")
                edq.util.dirent.mkdir(base_dir)

                # Write the dict config to disk.
                config_path = os.path.join(base_dir, 'config.json')
                edq.util.json.dump_path(expected_dict_config, config_path)

                # Load the tiered config.
                # Note that they encryption key is passed via an environmental variable.
                tiered_config = edq.config.load.get_tiered_config(
                    cli_arguments = {edq.config.constants.GLOBAL_CONFIG_KEY: config_path},
                )

                # Ignore some config fields by setting them equal.
                ignore_fields = ['encryption_key']
                for ignore_field in ignore_fields:
                    value = getattr(tiered_config.application_config, ignore_field)

                    setattr(expected_application_config, ignore_field, value)
                    expected_dict_config[ignore_field] = value

                # Ensure that the loaded application config matches the expected application config.
                self.assertJSONEqual(expected_application_config, tiered_config.application_config)

                # Serialize the application config, and ensure it matches the dict config.
                new_dict_config = tiered_config.application_config.to_dict(context = serialization_context)
                self.assertJSONDictEqual(expected_dict_config, new_dict_config)

                # Deserialize the dict config into an application config, and ensure it matches the application config.
                new_application_config = edq.config.testing.TestApplicationConfig.from_dict(new_dict_config, context = serialization_context)
                self.assertEqual(tiered_config.application_config, new_application_config)
