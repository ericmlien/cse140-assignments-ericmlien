import enum
import typing

def has_value(enum_class: typing.Type[enum.Enum], value: typing.Any) -> bool:
    """ Check if the given value is one of the possible values for the given enum. """

    # If the value is already a member of the target class, just check normal membership.
    if (isinstance(value, enum_class) and (value in enum_class)):
        return True

    # If the value is from a different enum class, then skip the value check.
    if (isinstance(value, enum.Enum) and (not isinstance(value, enum_class))):
        return False

    enum_values = {member.value for member in enum_class}
    return (value in enum_values)
