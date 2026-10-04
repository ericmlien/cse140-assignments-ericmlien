"""
This file standardizes how we write and read JSON.
Specifically, we try to be flexible when reading (using JSON5),
and strict when writing (using vanilla JSON).
"""

import enum
import gzip
import io
import json
import os
import typing

import json5

import edq.util.common
import edq.util.dirent

def load(
        file_obj: typing.IO,
        strict: bool = False,
        gzipped: bool = False,
        encoding: str = edq.util.dirent.DEFAULT_ENCODING,
        **kwargs: typing.Any) -> typing.Any:
    """
    Load a file object/handler as JSON.
    If strict is set, then use standard Python JSON,
    otherwise use JSON5.

    If `gzipped` is set, the file object is treated as a gzipped bytes stream (e.g. `open('test.json.gz', 'rb')`).
    """

    if (gzipped):
        binary_file_obj = gzip.GzipFile(fileobj = file_obj)
        file_obj = io.TextIOWrapper(binary_file_obj, encoding = encoding)

    if (strict):
        return json.load(file_obj, **kwargs)

    return json5.load(file_obj, **kwargs)

def loads(text: str, strict: bool = False, **kwargs: typing.Any) -> typing.Any:
    """
    Load a string as JSON.
    If strict is set, then use standard Python JSON,
    otherwise use JSON5.
    """

    if (strict):
        return json.loads(text, **kwargs)

    return json5.loads(text, **kwargs)

def load_path(
        path: str,
        strict: bool = False,
        gzipped: typing.Union[bool, None] = None,
        encoding: str = edq.util.dirent.DEFAULT_ENCODING,
        **kwargs: typing.Any) -> typing.Any:
    """
    Load a file path as JSON.
    If strict is set, then use standard Python JSON,
    otherwise use JSON5.

    If `gzipped` is not set, the behavior is guessed from the extension (".gz").
    """

    if (not os.path.exists(path)):
        raise FileNotFoundError(f"File does not exist: '{path}'.")

    if (os.path.isdir(path)):
        raise IsADirectoryError(f"Cannot open JSON file, expected a file but got a directory at '{path}'.")

    if (gzipped is None):
        gzipped = (os.path.splitext(path)[-1] == '.gz')

    open_func = open
    if (gzipped):
        open_func = gzip.open  # type: ignore[assignment]

    with open_func(path, 'rt', encoding = encoding) as file:
        try:
            return load(file, strict = strict, **kwargs)
        except Exception as ex:
            raise ValueError(f"Failed to read JSON file '{path}'.") from ex

def json_serialization_handle(value: typing.Any) -> typing.Union[typing.Dict[str, typing.Any], str, typing.Any]:
    """
    Handle objects that are not JSON serializable by default,
    e.g., calling vars() on an object.
    This is meant to be used as the `default` argument to `json` stdlib dumping functions.
    """

    # If this looks like a edq.util.serial.DictSerializer.
    if (hasattr(value, 'to_dict')):
        return value.to_dict(edq.util.common.SerializationContext())

    # If this looks like a edq.util.serial.PODSerializer.
    if (hasattr(value, 'to_pod')):
        return value.to_pod(edq.util.common.SerializationContext())

    if (isinstance(value, enum.Enum)):
        return str(value)

    if (hasattr(value, '__dict__')):
        return dict(vars(value))

    raise ValueError(f"Could not JSON serial object: '{value}'.")

def dump(
        data: typing.Any,
        file_obj: typing.TextIO,
        default: typing.Union[typing.Callable, None] = json_serialization_handle,
        sort_keys: bool = True,
        **kwargs: typing.Any) -> None:
    """ Dump an object as a JSON file object. """

    json.dump(data, file_obj, default = default, sort_keys = sort_keys, **kwargs)

def dumps(
        data: typing.Any,
        default: typing.Union[typing.Callable, None] = json_serialization_handle,
        sort_keys: bool = True,
        **kwargs: typing.Any) -> str:
    """ Dump an object as a JSON string. """

    return json.dumps(data, default = default, sort_keys = sort_keys, **kwargs)

def dump_path(
        data: typing.Any,
        path: str,
        default: typing.Union[typing.Callable, None] = json_serialization_handle,
        sort_keys: bool = True,
        gzipped: typing.Union[bool, None] = None,
        encoding: str = edq.util.dirent.DEFAULT_ENCODING,
        **kwargs: typing.Any) -> None:
    """
    Dump an object as a JSON file.

    If `gzipped` is not set, the behavior is guessed from the extension (".gz").
    """

    if (gzipped is None):
        gzipped = (os.path.splitext(path)[-1] == '.gz')

    open_func = open
    if (gzipped):
        open_func = gzip.open  # type: ignore[assignment]

    with open_func(path, 'wt', encoding = encoding) as file:
        dump(data, file, default = default, sort_keys = sort_keys, **kwargs)
