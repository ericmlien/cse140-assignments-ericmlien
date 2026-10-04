"""
Common files for utils.

Objects are often placed here to break circular dependencies.
"""

import copy
import typing

class SerializationContext:
    """
    Context information (context and options) to aid the serialization process.
    An instance of this class will be passed around the core serialization functions to provide context and extra options.
    """

    def __init__(self,
            base_dir: typing.Union[str, None] = None,
            source_path: typing.Union[str, None] = None,
            key: typing.Union[str, None] = None,
            json_options: typing.Union[typing.Dict[str, typing.Any], None] = None,
            extra: typing.Union[typing.Dict[str, typing.Any], None] = None,
            **kwargs: typing.Any) -> None:
        if (base_dir is None):
            base_dir = '.'

        self.base_dir: str = base_dir
        """
        The base directory for any relative paths this object needs to resolve.
        Defaults to '.'.
        """

        self.source_path: typing.Union[str, None] = source_path
        """ If we are reading from a file, this attribute should be the absolute path to that file. """

        self.key: typing.Union[str, None] = key
        """
        An key to use during (de)serialization.
        For example, this may be an encryption key.
        """

        if (json_options is None):
            json_options = {}

        self.json_options: typing.Dict[str, typing.Any] = json_options
        """ Options to pass to JSON functions. """

        if (extra is None):
            extra = {}
        else:
            extra = extra.copy()

        extra.update(kwargs)

        self.extra: typing.Dict[str, typing.Any] = extra
        """
        Additional data to pass along the serialization process.
        This is where users can pass additional data.
        """

    def copy(self) -> 'SerializationContext':
        """ Make a deep copy of this context. """

        return copy.deepcopy(self)
