import typing

import edq.testing.unittest
import edq.util.crypto
import edq.util.encoding
import edq.util.serial

class CryptoTest(edq.testing.unittest.BaseTest):
    """ Test cryptographic functions. """

    def test_secret_serialization_base(self) -> None:
        """ Test the basics of secret (de)serialization. """

        # [(secret, key, error substring), ...]
        test_cases: typing.List[typing.Tuple[
                edq.util.crypto.Secret,
                typing.Union[str, None],
                typing.Union[str, None],
        ]] = [
            # Cleartext
            (
                edq.util.crypto.Secret("secret"),
                None,
                None,
            ),

            # Generate IV/Salt
            (
                edq.util.crypto.Secret("secret", write_encrypted = True),
                'key',
                None,
            ),

            # Existing IV/Salt
            (
                edq.util.crypto.Secret(
                    "secret",
                    iv_b64 = 'UldcITh761FJcMRThJpkag==',
                    salt_b64 = 'niOb2keWPoSwR1MlgWHayQ==',
                ),
                'key',
                None,
            ),

            # Error - No Key
            (
                edq.util.crypto.Secret("secret", write_encrypted = True),
                None,
                'No key provided for writing an encrypted secret',
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            (first_secret, key, error_substring) = test_case

            with self.subTest(msg = f"Case {i}:"):
                context = edq.util.serial.SerializationContext(key = key)

                try:
                    second_text = first_secret.to_pod(context)
                    second_secret = edq.util.crypto.Secret.from_pod(second_text, context)

                    third_text = second_secret.to_pod(context)
                    third_secret = edq.util.crypto.Secret.from_pod(third_text, context)
                except Exception as ex:
                    error_string = self.format_error_string(ex)
                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

                # The cleartext should always be the same.
                # The first may not have a salt/iv, but second the third should be identical.
                self.assertEqual(first_secret.cleartext, second_secret.cleartext)
                self.assertEqual(second_secret, third_secret)

                # The same serilziation text should have been produced.
                self.assertEqual(second_text, third_text)

    def test_secret_deserialization_special(self) -> None:
        """ Test special cases of secret deserialization. """

        # [(serial text, key, expected cleartext, error substring), ...]
        test_cases: typing.List[typing.Tuple[
                str,
                typing.Union[str, None],
                typing.Union[str, None],
                typing.Union[str, None],
        ]] = [
            # Base - Unencrypted
            (
                'secret',
                None,
                'secret',
                None,
            ),

            # Base - Encrypted
            (
                '__edq_secret__::AES256v1::UldcITh761FJcMRThJpkag==::niOb2keWPoSwR1MlgWHayQ==::sN3Tl4WCA6X+xszcnTO+9Q==',
                'key',
                'secret',
                None,
            ),

            # Bad Key
            (
                '__edq_secret__::AES256v1::UldcITh761FJcMRThJpkag==::niOb2keWPoSwR1MlgWHayQ==::sN3Tl4WCA6X+xszcnTO+9Q==',
                'ZZZ',
                None,
                'Decryption failed',
            ),

            # Bad IV
            (
                '__edq_secret__::AES256v1::ZZZcITh761FJcMRThJpkag==::niOb2keWPoSwR1MlgWHayQ==::sN3Tl4WCA6X+xszcnTO+9Q==',
                'key',
                None,
                'Decryption failed',
            ),

            # Bad Salt
            (
                '__edq_secret__::AES256v1::UldcITh761FJcMRThJpkag==::ZZZb2keWPoSwR1MlgWHayQ==::sN3Tl4WCA6X+xszcnTO+9Q==',
                'key',
                None,
                'Decryption failed',
            ),

            # No Key
            (
                '__edq_secret__::AES256v1::UldcITh761FJcMRThJpkag==::niOb2keWPoSwR1MlgWHayQ==::sN3Tl4WCA6X+xszcnTO+9Q==',
                None,
                None,
                'No key provided',
            ),

            # Malformed - Bad Method
            (
                '__edq_secret__::ZZZ::UldcITh761FJcMRThJpkag==::niOb2keWPoSwR1MlgWHayQ==::sN3Tl4WCA6X+xszcnTO+9Q==',
                'key',
                None,
                'unknown encryption method',
            ),

            # Malformed - Not Enough Parts,
            (
                '__edq_secret__::AES256v1::UldcITh761FJcMRThJpkag==::niOb2keWPoSwR1MlgWHayQ==',
                'key',
                None,
                'unexpected number of parts',
            ),

            # Malformed - Too Many Parts,
            (
                '__edq_secret__::AES256v1::UldcITh761FJcMRThJpkag==::niOb2keWPoSwR1MlgWHayQ==::sN3Tl4WCA6X+xszcnTO+9Q==::foo',
                'key',
                None,
                'unexpected number of parts',
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            (text, key, expected_cleartext, error_substring) = test_case

            with self.subTest(msg = f"Case {i} ('{text}'):"):
                context = edq.util.serial.SerializationContext(key = key)

                try:
                    secret = edq.util.crypto.Secret.from_pod(text, context)
                except Exception as ex:
                    error_string = self.format_error_string(ex)
                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

                self.assertEqual(expected_cleartext, secret.cleartext)

    def test_aes256_base(self) -> None:
        """ Test base encryption and decryptin with AES256. """

        # [(key, iv, salt, cleartext, error substring), ...]
        test_cases: typing.List[typing.Tuple[
                str,
                typing.Union[str, None],
                typing.Union[str, None],
                str,
                typing.Union[str, None],
        ]] = [
            # Base
            (
                'key',
                edq.util.encoding.to_base64('iv'),
                edq.util.encoding.to_base64('salt'),
                'abc123',
                None,
            ),
            (
                'key2',
                edq.util.encoding.to_base64('iv'),
                edq.util.encoding.to_base64('salt'),
                'abc123',
                None,
            ),

            # Multiple Blocks
            (
                'key',
                edq.util.encoding.to_base64('iv'),
                edq.util.encoding.to_base64('salt'),
                'a' * int(edq.util.crypto.AES_BLOCK_SIZE_BYTES * 1.5),
                None,
            ),
            (
                'key',
                edq.util.encoding.to_base64('iv'),
                edq.util.encoding.to_base64('salt'),
                'a' * edq.util.crypto.AES_BLOCK_SIZE_BYTES * 2,
                None,
            ),
            (
                'key',
                edq.util.encoding.to_base64('iv'),
                edq.util.encoding.to_base64('salt'),
                'a' * int(edq.util.crypto.AES_BLOCK_SIZE_BYTES * 2.5),
                None,
            ),

            # Optional Field Generation
            (
                'key',
                None,
                edq.util.encoding.to_base64('salt'),
                'abc123',
                None,
            ),
            (
                'key',
                edq.util.encoding.to_base64('iv'),
                None,
                'abc123',
                None,
            ),
            (
                'key',
                None,
                None,
                'abc123',
                None,
            ),

            # Empty
            (
                '',
                '',
                '',
                '',
                None,
            ),
            (
                'key',
                edq.util.encoding.to_base64('iv'),
                edq.util.encoding.to_base64('salt'),
                '',
                None,
            ),
            (
                'key',
                '',
                '',
                '',
                None,
            ),
            (
                '',
                edq.util.encoding.to_base64('iv'),
                '',
                '',
                None,
            ),
            (
                '',
                '',
                edq.util.encoding.to_base64('salt'),
                '',
                None,
            ),
            (
                '',
                '',
                '',
                'abc',
                None,
            ),
        ]

        # Ensure that no duplicate ciphertexts are found.
        seen_ciphertexts: typing.Set[str] = set()

        for (i, test_case) in enumerate(test_cases):
            (key, iv, salt, cleartext, error_substring) = test_case

            with self.subTest(msg = f"Case {i} ('{cleartext}'):"):
                try:
                    ciphertext, actual_iv, actual_salt = edq.util.crypto.aes256_encrypt(key, cleartext, iv_b64 = iv, salt_b64 = salt)
                    actual = edq.util.crypto.aes256_decrypt(key, actual_iv, actual_salt, ciphertext)
                except Exception as ex:
                    error_string = self.format_error_string(ex)
                    if (error_substring is None):
                        self.fail(f"Unexpected error: '{error_string}'.")

                    self.assertIn(error_substring, error_string, 'Error is not as expected.')

                    continue

                if (error_substring is not None):
                    self.fail(f"Did not get expected error: '{error_substring}'.")

                self.assertEqual(cleartext, actual)

                if (iv is not None):
                    self.assertEqual(iv, actual_iv)

                if (salt is not None):
                    self.assertEqual(salt, actual_salt)

                self.assertNotIn(ciphertext, seen_ciphertexts, 'Found duplicate ciphertext.')
                seen_ciphertexts.add(ciphertext)
