import typing

BOOL_TRUE_STRINGS: typing.Set[str] = {
    'true', 't',
    'yes', 'y',
    '1',
}

BOOL_FALSE_STRINGS: typing.Set[str] = {
    'false', 'f',
    'no', 'n',
    '0',
}

def soft_boolean(raw_text: typing.Union[bool, str, typing.Any]) -> typing.Union[bool, None]:
    """
    Parse a boolean from a string using common string representations for true/false.
    If the input is not a bool or str, it will be converted to a str.
    This function assumes the entire string is the boolean (not just a part of it).
    If the string is not true or false, then return None.
    """

    if (isinstance(raw_text, bool)):
        return raw_text

    text = str(raw_text).lower().strip()

    if (text in BOOL_TRUE_STRINGS):
        return True

    if (text in BOOL_FALSE_STRINGS):
        return False

    return None

def boolean(raw_text: typing.Union[str, bool]) -> bool:
    """
    Like soft_boolean(), but raise an exception if no boolean is parsed.
    """

    value = soft_boolean(raw_text)
    if (value is not None):
        return value

    raise ValueError(f"Could not convert text to boolean: '{raw_text}'.")
