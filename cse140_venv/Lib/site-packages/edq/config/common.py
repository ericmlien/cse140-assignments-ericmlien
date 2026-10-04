#pylint: disable=invalid-name

"""
This module houses common information, mainly for the purpose of breaking dependency cycles.
Users should strongly prefer `edq.config.settings` over this module.
"""

import abc
import typing

import platformdirs

import edq.config.constants
import edq.util.serial

_DEFAULT_CONFIG_FILENAME: str = 'edq-config.json'
_config_filename: str = _DEFAULT_CONFIG_FILENAME

_DEFAULT_DEFAULT_ENCRYPTION_KEY: str = 'edq'
_default_encryption_key: str = _DEFAULT_DEFAULT_ENCRYPTION_KEY

_DEFAULT_ENV_PREFIX: str = 'EDQ__'
_env_prefix: str = _DEFAULT_ENV_PREFIX

_DEFAULT_GLOBAL_DIR: str = platformdirs.user_config_dir()
_global_dir: str = _DEFAULT_GLOBAL_DIR

class InternalApplicationConfig(edq.util.serial.DictConverter):
    """
    An internal-only class for breaking dependency cycles.
    See edq.config.app.BaseApplicationConfig for information about application configs.
    """

    serialization_skip_fields = {
        '_extra',
    }

    def __init__(self,
            encryption_key: typing.Union[str, None] = None,
            debug: typing.Union[bool, None] = None,
            log_level: typing.Union[str, None] = None,
            quiet: typing.Union[bool, None] = None,
            **kwargs: typing.Any) -> None:
        if (encryption_key is None):
            encryption_key = _default_encryption_key

        self.encryption_key: str = encryption_key
        """ The encryption key to use for config secrets. """

        self.debug: typing.Union[bool, None] = debug
        """ If extra debugging (e.g., logging) information should be provided. """

        self.log_level: typing.Union[str, None] = log_level
        """ The log level this program was started with. """

        self.quiet: typing.Union[bool, None] = quiet
        """ If the logs should give reduced output. """

        self._extra: typing.Dict[str, typing.Any] = kwargs
        """ Config options that were not explicitly handled in the constructor. """

    def to_dict(self,
            context: typing.Union[edq.util.serial.SerializationContext, None] = None,
            ) -> typing.Dict[str, edq.util.serial.PODType]:
        if (context is None):
            context = edq.util.serial.SerializationContext()
        else:
            context = context.copy()

        if (context.key is None):
            context.key = self.encryption_key

        return super().to_dict(context)

class InternalConfigSourceSpec(abc.ABC, edq.util.serial.DictConverter):
    """
    An internal-only class for breaking dependency cycles.
    See edq.config.source.ConfigSourceSpec for information about config source specifications.
    """

    label: str = ''
    """
    A label set by each subclass to identify the type of source spec.
    Generally, a user-friendly version of the class name.
    """

    def __init__(self) -> None:
        if (len(self.label) == 0):
            raise ValueError(f"ConfigSourceSpec child class ({type(self)}) did not set label.")

        self.type: str = self.label
        """ A label identifying the type of source this is (mainly used for identification during serialization). """

    @abc.abstractmethod
    def get_help_lines(self) -> typing.List[str]:
        """
        Get lines of text describing how this source is loaded.
        This text is intended to be used in a help prompt.
        """

# Will be set by edq.config.app on import.
_DEFAULT_APPLICATION_CONFIG_CLASS: typing.Type[InternalApplicationConfig] = InternalApplicationConfig
_application_config_class: typing.Type[InternalApplicationConfig] = _DEFAULT_APPLICATION_CONFIG_CLASS

# Will be set by edq.config.source on import.
_DEFAULT_LOAD_ORDER: typing.List[InternalConfigSourceSpec] = []
_load_order: typing.List[InternalConfigSourceSpec] = _DEFAULT_LOAD_ORDER.copy()
