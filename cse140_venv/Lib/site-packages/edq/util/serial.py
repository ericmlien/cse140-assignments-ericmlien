import collections
import enum
import os
import types
import typing

import edq.core.errors

import edq.util.common
import edq.util.enum
import edq.util.json

PODType = typing.Union[bool, float, int, str, typing.List['PODType'], typing.Dict[str, 'PODType'], None]  # pylint: disable=invalid-name
""" A "Plain Old Data" type that can be easily represented (e.g., in JSON). """

SerializationBaseClass = typing.TypeVar('SerializationBaseClass', bound = 'SerializationBase')

DictSerializerClass = typing.TypeVar('DictSerializerClass', bound = 'DictSerializer')
DictDeserializerClass = typing.TypeVar('DictDeserializerClass', bound = 'DictDeserializer')
DictConverterClass = typing.TypeVar('DictConverterClass', bound = 'DictConverter')

PODSerializerClass = typing.TypeVar('PODSerializerClass', bound = 'PODSerializer')
PODDeserializerClass = typing.TypeVar('PODDeserializerClass', bound = 'PODDeserializer')
PODConverterClass = typing.TypeVar('PODConverterClass', bound = 'PODConverter')

# Alias the context (which we don't store here because of a cyclic dependency with edq.util.json).
SerializationContext = edq.util.common.SerializationContext

# For Python 3.9 compatibility, we need to dynamically check for which union types are available.
_UNION_TYPES: typing.Set[typing.Any] = {typing.Union}
if (hasattr(types, 'UnionType')):
    _UNION_TYPES.add(getattr(types, 'UnionType'))

class SerializationBase:
    """
    A base class for the serialization classes.

    Note that this causes diamond inheritance for classes that extend *Converter,
    but since this class only provides simple functionality not overwritten by any branch child,
    there should be no issues.

    General (but inefficient) implementations of several core Python equality, comparison, and representation methods are provided.
    A default hash implementation is provided, but it is up to child classes themselves to ensure they are immutable
    if they want to be used as set elements or dict keys.
    """

    serialization_omit_empty: bool = False
    """
    Do not include empty fields in serialization.
    An empty field meets one of the following conditions:
     - Has a `__len__` method which returns 0.
     - Has a `_serialization_is_empty` method that returns true.
    """

    serialization_omit_none: bool = False
    """ Do not include None (null) fields in serialization. """

    serialization_skip_fields: typing.Union[typing.Set[str], None] = None
    """ A list of field names to skip. """

    serialization_include_init_context: bool = False
    """ Do not send the serialization context to an object's init. """

    serialization_error_class: typing.Type[Exception] = ValueError
    """ The class to use when raising errors. """

    @classmethod
    def skip_field(cls, name: str, value: typing.Any) -> bool:
        """ Check if a field should be skipped. """

        if ((cls.serialization_skip_fields is not None) and (name in cls.serialization_skip_fields)):
            return True

        if (cls.serialization_omit_none and (value is None)):
            return True

        if (cls.serialization_omit_empty and hasattr(value, '__len__') and (len(value) == 0)):
            return True

        if (cls.serialization_omit_empty and hasattr(value, '_serialization_is_empty') and value._serialization_is_empty()):
            return True

        return False

    def __lt__(self, other: 'SerializationBase') -> bool:
        return repr(self) < repr(other)

    def __hash__(self) -> int:
        return hash(repr(self))

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return edq.util.json.dumps(self)

    def _eq(self,
            other: object,
            self_serializer: typing.Callable,
            other_serializer: typing.Callable,
            context: typing.Union[SerializationContext, None] = None,
            ) -> bool:
        """
        Check for equality using the given func..
        """

        if (not isinstance(other, type(self))):
            return False

        return bool(self_serializer(context) == other_serializer(context))

    @classmethod
    def _from_path(cls: typing.Type[SerializationBaseClass],
            path: str,
            deserializer: typing.Callable,
            context: typing.Union[SerializationContext, None] = None,
            ) -> SerializationBaseClass:
        """
        The internal helper for from_path().
        """

        path = os.path.abspath(path)

        if (context is None):
            context = SerializationContext()
        else:
            context = context.copy()

        context.base_dir = os.path.dirname(path)
        context.source_path = path

        data = edq.util.json.load_path(path, **context.json_options)

        return deserializer(data, context)  # type: ignore[no-any-return]

    def _to_path(self,
            path: str,
            serializer: typing.Callable,
            context: typing.Union[SerializationContext, None] = None,
            ) -> None:
        """ Write this object to the given path as JSON. """

        if (context is None):
            context = SerializationContext()
        else:
            context = context.copy()

        if ((not os.path.isabs(path)) and (context.base_dir is not None)):
            path = os.path.join(context.base_dir, path)

        context.source_path = os.path.abspath(path)
        context.base_dir = os.path.dirname(context.source_path)

        data = serializer(context)
        edq.util.json.dump_path(data, context.source_path, **context.json_options)

class PODSerializer(SerializationBase):
    """
    A class that can represent itself as a POD type.
    Sibling to PODDeserializer.
    """

    def to_pod(self,
            context: typing.Union[SerializationContext, None] = None,
            ) -> PODType:
        """
        Get a POD representation of this object.

        The default implementation will convert to a dict (similar to a DictSerializer).
        """

        if (context is None):
            context = SerializationContext()

        data: typing.Dict[str, typing.Any] = {}

        for (key, value) in vars(self).items():
            if (self.skip_field(key, value)):
                continue

            data[key] = generic_to_pod(value, context, self.serialization_error_class)

        return data

    def to_path(self,
            path: str,
            context: typing.Union[SerializationContext, None] = None,
            ) -> None:
        """ Write this object to the given path as JSON. """

        self._to_path(path, self.to_pod, context)

    def __eq__(self, other: object) -> bool:
        """
        Check for equality.

        This check uses to_pod() and compares the results.
        This may not be complete or efficient depending on the child class.
        """

        return self._eq(other, self.to_pod, getattr(other, 'to_pod', None))  # type: ignore[arg-type]

class PODDeserializer(SerializationBase):
    """
    A class that can construct itself from a POD type.
    Sibling to PODSerializer.
    """

    @classmethod
    def prep_init_data(cls,
            data: typing.Dict[str, typing.Any],
            context: typing.Union[SerializationContext, None] = None,
            ) -> typing.Dict[str, typing.Any]:
        """
        Prepare data to be passed into this class' constructor.

        By default, this is called by from_pod().
        A child can override this or prep_init_data() depending on the functionality they want.

        A general (but inefficient) implementation is provided by default.
        This implementation will attempt to use type hints (of the classes constructor) to convert enums and DictDeserializers.
        """

        if (context is None):
            context = SerializationContext()

        new_data = {}
        constructor_types = typing.get_type_hints(cls.__init__)

        for (key, value) in data.items():
            if (cls.skip_field(key, value)):
                continue

            new_data[key] = _from_pod(f"field {key}", constructor_types.get(key, None), value, context, cls.serialization_error_class)

        return new_data

    @classmethod
    def from_pod(cls: typing.Type[PODDeserializerClass],
            data: PODType,
            context: typing.Union[SerializationContext, None] = None,
            ) -> PODDeserializerClass:
        """
        Create an instance of this class from a POD.

        The default implementation will call the class' constructor with one of two things:
        a splat/unpacking (**) of the incoming data if the data is a dict,
        otherwise the data itself.
        """

        if (context is None):
            context = SerializationContext()

        if (isinstance(data, dict)):
            new_data = cls.prep_init_data(data, context)

            if (cls.serialization_include_init_context):
                new_data['context'] = context

            return cls(**new_data)

        return cls(data)  # type: ignore[call-arg]

    @classmethod
    def from_path(cls: typing.Type[PODDeserializerClass],
            path: str,
            context: typing.Union[SerializationContext, None] = None,
            ) -> PODDeserializerClass:
        """
        Read the path (as JSON) and call from_pod().

        If a serialization context is passed in to this function,
        a copy will be made with the new base dir and source path.
        """

        return cls._from_path(path, cls.from_pod, context)

class PODConverter(PODSerializer, PODDeserializer):
    """ A PODSerializer and PODDeserializer. """

    def copy(self,
            context: typing.Union[SerializationContext, None] = None,
            ) -> 'PODConverter':
        """
        Make a deep copy of this object.
        The default implementation will use to_pod() and from_pod() to make a copy.

        Callers should be cautious of fileds that are skipped in serialization,
        e.g., via `SerializationBase.serialization_skip_fields`.
        """

        if (context is None):
            context = SerializationContext()

        return self.from_pod(self.to_pod(context), context)

class DictSerializer(PODSerializer):
    """
    A base class for class that can represent itself as a dict.
    The intention is that the dict can then be cleanly converted to/from JSON.
    """

    def to_dict(self,
            context: typing.Union[SerializationContext, None] = None,
            ) -> typing.Dict[str, PODType]:
        """
        Return a dict that can be used to represent this object.
        If the dict is passed to from_dict(), an identical object should be reconstructed.

        A general (but inefficient) implementation is provided by default.
        """

        data = self.to_pod(context)
        if (not isinstance(data, dict)):
            raise self.serialization_error_class(f"DictSerializer's to_pod() did not return a dict, found '{type(data)}'.")

        return data

    def to_path(self,
            path: str,
            context: typing.Union[SerializationContext, None] = None,
            ) -> None:
        """ Write this object to the given path as JSON. """

        self._to_path(path, self.to_dict, context)

    def __eq__(self, other: object) -> bool:
        """
        Check for equality.

        This check uses to_pod() and compares the results.
        This may not be complete or efficient depending on the child class.
        """

        return self._eq(other, self.to_dict, getattr(other, 'to_dict', None))  # type: ignore[arg-type]

class DictDeserializer(PODDeserializer):
    """
    A base class for class that can reconstruct (deserialize) themselves from a dict.
    The intention is that the class can be cleanly converted from JSON.

    Any class that uses the default implementations should have a constructor
    that accepts arguments with the same name as their members.
    It is generally recommended to also have the constructor accept a kwargs,
    since values will be blindly passed to the constructor.
    """

    @classmethod
    def from_dict(cls: typing.Type[DictDeserializerClass],
            data: typing.Dict[str, PODType],
            context: typing.Union[SerializationContext, None] = None,
            ) -> DictDeserializerClass:
        """
        Return an instance of this subclass created using the given dict.
        If the dict came from to_dict(), the returned object should be equivalent to the original.

        By default, this function just calls the class' constructor with the output of prep_init_data().
        A child can override this or prep_init_data() depending on the functionality they want.

        A general (but inefficient) implementation is provided by default.
        This implementation will attempt to use type hints (of the classes constructor) to convert enums and DictDeserializers.
        """

        return cls.from_pod(data, context)

    @classmethod
    def from_path(cls: typing.Type[DictDeserializerClass],
            path: str,
            context: typing.Union[SerializationContext, None] = None,
            ) -> DictDeserializerClass:
        """
        Read the path (as JSON) and call from_dict().

        If a serialization context is passed in to this function,
        a copy will be made with the new base dir and source path.
        """

        return cls._from_path(path, cls.from_dict, context)

class DictConverter(PODConverter, DictSerializer, DictDeserializer):
    """ A DictSerializer and DictDeserializer. """

def _check_issubclass(allowed_type: typing.Any, target: typing.Type) -> bool:
    """
    Call issubclass(), but squash and type errors.
    issubclass() can be picky about the input types is accepts.
    """

    if (allowed_type is None):
        return False

    try:
        return issubclass(allowed_type, target)
    except TypeError:
        return False

def generic_to_pod(
        raw_value: typing.Any,
        context: SerializationContext,
        serialization_error_class: typing.Type[Exception] = ValueError,
        ) -> PODType:
    """
    Attempt to convert a value to a POD type.

    Has special handling for:
        - DictSerializer
        - PODSerializer
        - enum.Enum
        - (list, tuple, set)
        - dict
    """

    if (raw_value is None):
        return None

    # Simple types that are already POD.
    if (isinstance(raw_value, (bool, float, int, str))):
        return raw_value

    if (isinstance(raw_value, DictSerializer)):
        return raw_value.to_dict(context)

    if (isinstance(raw_value, PODSerializer)):
        return raw_value.to_pod(context)

    if (isinstance(raw_value, enum.Enum)):
        return generic_to_pod(raw_value.value, context, serialization_error_class)

    if (isinstance(raw_value, (list, tuple, set))):
        items = [generic_to_pod(item, context, serialization_error_class) for item in raw_value]

        # Sort sets for consistency.
        if (isinstance(raw_value, set)):
            # Sort using the string representation of the items (since the set could be heterogeneous and have non-comparable items).
            sort_list = sorted([(item, i) for (i, item) in enumerate(map(str, items))])
            items = [items[i] for (_, i) in sort_list]

        return items

    if (isinstance(raw_value, dict)):
        return {key: generic_to_pod(value, context, serialization_error_class) for (key, value) in raw_value.items()}

    raise serialization_error_class(f"Unable to convert value to simple (edq.util.serial.POD) type: '{raw_value}' (type: '{type(raw_value)}').")

def _from_pod(
        label: str,
        type_hint: typing.Any,
        raw_value: typing.Any,
        context: SerializationContext,
        serialization_error_class: typing.Type[Exception] = ValueError,
        ) -> typing.Any:
    """ Attempt to convert a value to the hinted value. """

    try:
        return _from_pod_internal(label, type_hint, raw_value, context, serialization_error_class)
    except Exception as ex:
        raise serialization_error_class(f"Failed to deserialize {label}.") from ex

def _from_pod_internal(
        label: str,
        type_hint: typing.Any,
        raw_value: typing.Any,
        context: SerializationContext,
        serialization_error_class: typing.Type[Exception] = ValueError,
        ) -> typing.Any:
    """ Attempt to convert a value to the hinted value. """

    # If there is no type hint or anything is allowed, then just return the raw value.
    if ((type_hint is None) or (type_hint is typing.Any)):
        return raw_value

    allowed_types: typing.Tuple[typing.Any, ...] = tuple([type_hint])

    # Check if the hint is a union.
    if (typing.get_origin(type_hint) in _UNION_TYPES):
        allowed_types = typing.get_args(type_hint)

    if (len(allowed_types) == 0):
        return raw_value

    # Check for a None early.
    if ((raw_value is None) and (type(None) in allowed_types)):
        return None

    # Check each possible type and match the first one.
    for allowed_type in allowed_types:
        if (_check_issubclass(allowed_type, DictDeserializer) and isinstance(raw_value, dict)):
            return allowed_type.from_dict(raw_value, context)

        if (_check_issubclass(allowed_type, PODDeserializer)):
            return allowed_type.from_pod(raw_value, context)

        if (_check_issubclass(allowed_type, enum.Enum)):
            if (edq.util.enum.has_value(allowed_type, raw_value)):
                return allowed_type(raw_value)

        # Sequence container types.
        if ((typing.get_origin(allowed_type) in (list, tuple, set, collections.abc.Sequence)) and isinstance(raw_value, (list, tuple, set))):
            collection_type = typing.get_origin(allowed_type)
            if (collection_type is collections.abc.Sequence):
                collection_type = list

            item_type = None
            args = typing.get_args(allowed_type)
            if (len(args) > 0):
                item_type = args[0]

            return collection_type([
                _from_pod(f"{label}[{i}]", item_type, item, context, serialization_error_class)
                for (i, item)
                in enumerate(raw_value)
            ])

        # Dict
        if ((typing.get_origin(allowed_type) in (dict, collections.abc.Mapping)) and isinstance(raw_value, dict)):
            key_type = None
            value_type = None

            args = typing.get_args(allowed_type)
            if (len(args) == 2):
                key_type = args[0]
                value_type = args[1]

            return {
                _from_pod(f"{label}.({key} (key))", key_type, key, context, serialization_error_class):
                _from_pod(f"{label}.{key}", value_type, value, context, serialization_error_class)
                for (key, value)
                in raw_value.items()
            }

    # No special conversion was made, try to force the first type.

    force_type = allowed_types[0]
    if (not isinstance(force_type, type)):
        force_type = typing.get_origin(force_type)

    if (force_type is not None):
        return force_type(raw_value)

    return raw_value
