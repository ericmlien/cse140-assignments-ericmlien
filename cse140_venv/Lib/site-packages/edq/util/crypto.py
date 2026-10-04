import enum
import hashlib
import logging
import os
import typing

import cryptography.hazmat.primitives
import cryptography.hazmat.primitives.ciphers
import cryptography.hazmat.primitives.padding

import edq.core.errors
import edq.util.constants
import edq.util.encoding
import edq.util.enum
import edq.util.serial

_logger = logging.getLogger(__name__)

SCRYPT_DEFAULT_ITERATIONS: int = 2**11
"""
The default iterations to use with scrypt.
2^11 or 2^14 are generally recommended for interactive tools.
"""

SCRYPT_DEFAULT_BLOCK_SIZE: int = 8
""" The default block size factor to use with scrypt. """

SCRYPT_PARALLELIZATION: int = 1
""" The parallelization (or lack thereof) to use in scrypt. """

SALT_LENGTH_BYTES: int = 16
""" The length for generated salts. """

IV_LENGTH_BYTES: int = 16
""" The length for generated IVs (before key derivation). """

AES_BLOCK_SIZE_BYTES: int = 16
""" AES always uses 128-bit blocks. """

SECRET_PREFIX: str = '__edq_secret__'
""" A string that must appear at the beginning of an encrypted secret. """

SECRET_DELIM: str = '::'
""" The delimiter for the components of an encrypted secret. """

class EncryptionMethod(enum.Enum):
    """ Supported encryption methods. """

    AES256v1 = 'AES256v1'  # pylint: disable=invalid-name

class Secret(edq.util.serial.PODConverter):
    """
    Secrets represent data that should be protected on disk.
    This type can be configured to always be serialized in an encrypted form.
    """

    def __init__(self,
            cleartext: str,
            iv_b64: typing.Union[str, None] = None,
            salt_b64: typing.Union[str, None] = None,
            encryption_method: EncryptionMethod = EncryptionMethod.AES256v1,
            write_encrypted: typing.Union[bool, None] = None,
            ) -> None:
        self.cleartext: str = cleartext
        """ The contexts of the secret. """

        self.iv_b64: typing.Union[str, None] = iv_b64
        """
        The base64 of the iv to use during encryption.
        May be none is this secret has not been encrypted yet,
        will be set during the first encryption.
        """

        self.salt_b64: typing.Union[str, None] = salt_b64
        """
        The base64 of the salt to use during encryption.
        May be none is this secret has not been encrypted yet,
        will be set during the first encryption.
        """

        self.encryption_method: EncryptionMethod = encryption_method
        """ The encryption method to use. """

        if (write_encrypted is None):
            write_encrypted = (salt_b64 is not None)

        self.write_encrypted: bool = write_encrypted
        """
        Whether to write (serialize) this secret in its encrypted form.
        If not explicitly set, this will be set based on if the passed in salt is null
        (if the salt not null, then encrypt).
        """

    def is_encrypted(self) -> bool:
        """
        Check if this secret is encrypted on disk.
        This is meant to be used by regular users who use parse().
        Advanced users may have to make their own checks.
        """

        return (self.salt_b64 is not None)

    def __repr__(self) -> str:
        return self.cleartext

    # Use generic dict serialization for equality.
    def __eq__(self, other: object) -> bool:
        if (not isinstance(other, Secret)):
            return False

        context = edq.util.serial.SerializationContext()
        return bool(super().to_pod(context) == super(edq.util.serial.PODConverter, other).to_pod(context))  # type: ignore[attr-defined,unused-ignore]

    def encrypt(self, key: str) -> str:
        """
        Get the full delimited and encrypted representation for this secret.
        If the IV and/or salt has not been set, this call will set them.
        """

        if (self.encryption_method == EncryptionMethod.AES256v1):
            ciphertext, self.iv_b64, self.salt_b64 = aes256_encrypt(key, self.cleartext, self.iv_b64, self.salt_b64)
        else:
            raise edq.core.errors.SerializationError(f"Secret has an unsupported encryption method: '{self.encryption_method}'.")

        parts: typing.List[str] = [
            SECRET_PREFIX,
            self.encryption_method.value,
            self.iv_b64,
            self.salt_b64,
            ciphertext,
        ]

        return SECRET_DELIM.join(parts)

    def to_pod(self,
            context: typing.Union[edq.util.serial.SerializationContext, None] = None,
            ) -> edq.util.serial.PODType:
        if (context is None):
            context = edq.util.serial.SerializationContext()

        if (not self.write_encrypted):
            return self.cleartext

        if (context.key is None):
            raise edq.core.errors.SerializationError("No key provided for writing an encrypted secret.")

        return self.encrypt(context.key)

    @classmethod
    def parse(cls, text: str, key: typing.Union[str, None] = None) -> 'Secret':
        """
        Parse a secret from text.
        A key is required if the text is encrypted.
        """

        text = text.strip()

        # Check for only cleartext.
        if (not text.startswith(SECRET_PREFIX)):
            return Secret(text)

        if (key is None):
            raise edq.core.errors.SerializationError("No key provided for reading an encrypted secret.")

        parts = text.split(SECRET_DELIM)
        if (len(parts) != 5):
            raise edq.core.errors.SerializationError(f"Secret has an unexpected number of parts, expecting 5 and found {len(parts)}: '{text}'.")

        (_, raw_method, iv_b64, salt_b64, ciphertext_b64) = parts

        if (not edq.util.enum.has_value(EncryptionMethod, raw_method)):
            raise edq.core.errors.SerializationError(f"Secret has an unknown encryption method: '{raw_method}'.")

        encryption_method = EncryptionMethod(raw_method)

        if (encryption_method == EncryptionMethod.AES256v1):
            cleartext = aes256_decrypt(key, iv_b64, salt_b64, ciphertext_b64)
        else:
            raise edq.core.errors.SerializationError(f"Secret has an unsupported encryption method: '{encryption_method}'.")

        return Secret(cleartext, iv_b64, salt_b64, encryption_method)

    @classmethod
    def from_pod(cls,
            data: edq.util.serial.PODType,
            context: typing.Union[edq.util.serial.SerializationContext, None] = None,
            ) -> 'Secret':
        if (not isinstance(data, str)):
            raise edq.core.errors.SerializationError(f"Secrets should be deserialized from a string, found a '{type(data)}' ({data}).")

        if (context is None):
            context = edq.util.serial.SerializationContext()

        return cls.parse(str(data), context.key)

def aes256_encrypt(
        key: str,
        cleartext: str,
        iv_b64: typing.Union[str, None] = None,
        salt_b64: typing.Union[str, None] = None,
        encoding: str = edq.util.constants.DEFAULT_ENCODING,
        ) -> typing.Tuple[str, str, str]:
    """
    Perform AES256-CBC encryption.
    Returns the base64 encoding of the ciphertext, iv, and salt.
    If the IV and/or salt are passed in, the same values will be passed back.
    """

    # Resolve optional fields.

    if (iv_b64 is None):
        iv_bytes = os.urandom(IV_LENGTH_BYTES)
    else:
        iv_bytes = edq.util.encoding.from_base64(iv_b64, encoding = encoding)

    if (salt_b64 is None):
        salt_bytes = os.urandom(SALT_LENGTH_BYTES)
    else:
        salt_bytes = edq.util.encoding.from_base64(salt_b64, encoding = encoding)

    # Derive fixed-sized keys from the key (32 bytes) and IV (16 bytes).
    aes_key = _derive_aes_key(key.encode(encoding), salt_bytes, 32)
    aes_iv = _derive_aes_key(iv_bytes, salt_bytes, AES_BLOCK_SIZE_BYTES)

    # Convert the cleartext to bytes and pad for a 256 block size.
    cleartext_bytes = cleartext.encode(encoding)
    padder = cryptography.hazmat.primitives.padding.PKCS7(8 * AES_BLOCK_SIZE_BYTES).padder()
    cleartext_bytes_padded = padder.update(cleartext_bytes) + padder.finalize()

    # Encrypt the data.
    cipher = cryptography.hazmat.primitives.ciphers.Cipher(
        cryptography.hazmat.primitives.ciphers.algorithms.AES(aes_key),
        cryptography.hazmat.primitives.ciphers.modes.CBC(aes_iv),
    )
    encryptor = cipher.encryptor()
    ciphertext_bytes = encryptor.update(cleartext_bytes_padded) + encryptor.finalize()

    # Encode the results in base64.
    ciphertext_b64 = edq.util.encoding.to_base64(ciphertext_bytes)
    iv_b64 = edq.util.encoding.to_base64(iv_bytes)
    salt_b64 = edq.util.encoding.to_base64(salt_bytes)

    return (ciphertext_b64, iv_b64, salt_b64)

def aes256_decrypt(
        key: str,
        iv_b64: str,
        salt_b64: str,
        ciphertext_b64: str,
        encoding: str = edq.util.constants.DEFAULT_ENCODING,
        ) -> str:
    """
    Perform AES256-CBC decryption.
    """

    # Get the input data as bytes.
    iv_bytes = edq.util.encoding.from_base64(iv_b64, encoding = encoding)
    salt_bytes = edq.util.encoding.from_base64(salt_b64, encoding = encoding)
    ciphertext_bytes = edq.util.encoding.from_base64(ciphertext_b64, encoding = encoding)

    # Derive fixed-sized keys from the key (32 bytes) and IV (16 bytes).
    aes_key = _derive_aes_key(key.encode(encoding), salt_bytes, 32)
    aes_iv = _derive_aes_key(iv_bytes, salt_bytes, AES_BLOCK_SIZE_BYTES)

    # Decrypt the data.
    cipher = cryptography.hazmat.primitives.ciphers.Cipher(
        cryptography.hazmat.primitives.ciphers.algorithms.AES(aes_key),
        cryptography.hazmat.primitives.ciphers.modes.CBC(aes_iv),
    )
    decryptor = cipher.decryptor()
    cleartext_bytes_padded = decryptor.update(ciphertext_bytes) + decryptor.finalize()

    # Unpad and decode the data.
    unpadder = cryptography.hazmat.primitives.padding.PKCS7(8 * AES_BLOCK_SIZE_BYTES).unpadder()
    try:
        cleartext_bytes = unpadder.update(cleartext_bytes_padded) + unpadder.finalize()
    except ValueError as ex:
        _logger.debug("Decryption failed.", exc_info = ex)
        raise edq.core.errors.UtilsError("Decryption failed. Do you have the correct key?")  # pylint: disable=raise-missing-from

    cleartext = cleartext_bytes.decode(encoding)

    return cleartext

def _derive_aes_key(
        key_bytes: bytes,
        salt: bytes,
        derived_key_length: int,
        iterations: int = SCRYPT_DEFAULT_ITERATIONS,
        block_size: int = SCRYPT_DEFAULT_BLOCK_SIZE,
        ) -> bytes:
    """ Derive a key for use in AES256 from a cleartext key and salt. """

    return hashlib.scrypt(
        key_bytes,
        salt = salt,
        n = iterations,
        r = block_size,
        p = SCRYPT_PARALLELIZATION,
        dklen = derived_key_length,
    )
