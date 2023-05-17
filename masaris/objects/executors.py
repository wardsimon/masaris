from __future__ import annotations

from inspect import signature

_author__ = "github.com/wardsimon"
__version__ = "0.1.0"

import abc
import logging

from copy import deepcopy
from numbers import Number
from typing import Optional, Tuple, Union, TYPE_CHECKING, Type, Any, List, NoReturn, Dict

from .core import ExecutorBase, Parameterized


if TYPE_CHECKING:
    from .variables import V
    from .core import Pcls, Pobj, E


class MyDict(dict):
    """A dictionary that allows you to set attributes on it."""
    pass


class Executor(ExecutorBase):
    """A class that allows you to define a variable that can be watched and executed on change."""
    def __init__(self, readonly: bool = False, visible: bool = True, inherit_watchers: bool = True, allow_none: bool = True,
                 read_modifiers: Optional[List[Callable]] = None, write_modifiers: Optional[List[Callable]] = None, **kwargs):
        """

        :param args: Arguments to pass to the base executor
        :param readonly: Can the value of the variable be changed?
        :param visible: Will the variable be visible in the list of parameters?
        :param inherit_watchers: Should the watchers be inherited from the parent class?
        :param allow_none: Can the value be None?
        :param kwargs: Key word arguments to pass to the base executor
        """
        super().__init__(read_modifiers=read_modifiers, write_modifiers=write_modifiers, **kwargs)
        self._readonly = readonly
        self._visible = visible
        self._inherit_watchers = inherit_watchers
        self._allow_none = allow_none

    def __set_name__(self, owner: Pcls, name: str):
        """
        Set the name of the variable on the owner class. This is called when the class is created. This attaches the
        executor to the class and makes sure that inheritance works correctly.
        :param owner: The owning class
        :param name: The name of the variable to be set to the class
        """

        # Name the executor and set the parent class
        self.name = name
        self.parent = owner

        # Check to see if the owner has a dictionary of descriptors
        descriptors = getattr(owner, "_descriptors", None)
        if descriptors is not None:
            # There is a dictionary, check to see if it is the correct one for this class
            if getattr(descriptors, "owner_class", None) != owner.__qualname__:
                # The dictionary is not the correct one, create a new one and add it to the class
                owner._descriptors = MyDict(**descriptors)
                setattr(owner._descriptors, "owner_class", owner.__qualname__)

            # Check to see if there is a class watcher...
            previous_executor = owner._descriptors.get(self.name, None)
            if previous_executor is not None:
                # There is a class watcher, check to see if it should be inherited
                if hasattr(previous_executor, "_class_executions") and len(
                        previous_executor._class_executions) > 0 and self._inherit_watchers:
                    # Inherit the class watchers
                    self._class_executions = deepcopy(previous_executor._class_executions)

            # Add the executor to the dictionary
            owner._descriptors[name] = self
        else:
            # If there is no dictionary, create one and add the executor to it
            setattr(owner, "_descriptors", MyDict())
            setattr(owner._descriptors, "owner_class", owner.__qualname__)
            owner._descriptors[name] = self

    def __get__(self, obj: Pobj, objtype: Optional = None):
        """
        Get the value of the variable (Executor). If the variable has not been initialised, return the default value.
        :param obj: The object that the variable is attached to.
        :param objtype:
        :return:
        """
        # Make sure that the object has been initialised
        if not hasattr(obj, "__params__"):
            # Not yet initialised, return the default value
            return self.value
        # Get the executor from the object
        if (executor := obj.__params__.get(self.name)) is not None:
            return executor.value
        return executor

    def __set__(self, obj: Pobj, value: Any):
        """
        Set the value of the variable. If the variable is readonly, raise an error.
        :param obj:
        :param value:
        :return:
        """
        if self._readonly:
            raise AttributeError("Cannot set a readonly attribute")
        if value is None and not self._allow_none:
            raise AttributeError("Cannot set a None value")
        if not hasattr(obj, "__params__"):
            raise AttributeError("Class does not have __params__. Is it based on Parameterized?")
        t_ = type(obj.__params__.get(self.name).value)
        tt_ = type(value)
        if issubclass(t_, Parameterized) and not issubclass(tt_, Parameterized):
            raise AttributeError("Cannot set a non Par to a class")
        executor = obj.__params__.get(self.name)
        executor.value = value

    @property
    def readonly(self) -> bool:
        """
        Defines if the variable is readonly.
        :return: Readonly status
        """
        return self._readonly

    @readonly.setter
    def readonly(self, readonly_status: bool) -> NoReturn:
        """
        Set the readonly status of the executor.
        :param readonly_status: New readonly status
        """
        self._readonly = readonly_status

    @property
    def allow_none(self) -> bool:
        """
        Defines if the variable can be set to None. This might be the default value.
        :return: Boolean value of the allow_none status
        """
        return self._allow_none

    @allow_none.setter
    def allow_none(self, new_allow_none_status: bool) -> NoReturn:
        """
        Set the allow_none status of the executor.
        :param new_allow_none_status:
        """
        self._allow_none = new_allow_none_status


class Typed(Executor):
    """
    Typed executor. This executor checks the type of the value that is being set against a predefined list of types.
    """
    def __init__(self, allowed_types: Union[type, Tuple[type]] = None, allow_subclasses: bool = False, **kwargs):
        """
        Initialise the executor with a list of types that the value can be and a flag to allow subclasses of types.
        This is off by default.
        :param args: Any arguments to pass to the base executor
        :param allowed_types: List of allowed types
        :param allow_subclasses: Is the value allowed to be a subclass of the allowed types?
        :param kwargs: Any keyword arguments to pass to the base executor
        """
        super().__init__(**kwargs)
        # Create a list of types that the value can be
        if allowed_types is None:
            allowed_types = object
        if not isinstance(allowed_types, tuple):
            allowed_types = (allowed_types,)
        self._types = allowed_types
        # State if subclasses are allowed
        self._allow_subclasses = allow_subclasses
        # Add the type check to the configuration
        self._configuration.append(self._check_type)

    def _check_type(self, parent: object, name: str, value: Any, extra: Optional[E] = None) -> NoReturn:
        """
        Type checking in the form of a base watcher which assigned to the configuration of the executor. This means that
        it is called FIRST when the value is set.
        :param parent: Object that the executor is attached to
        :param name: The name of the variable that the executor is attached to
        :param value: The new value that is being set
        :param extra: The executor, to obtain additional information.
        :return: No return as this watcher throws errors if the type is incorrect.
        """
        # Check the type of the value
        type_of_value = type(value)
        # Go through the list of allowed types. We iterate due to the possibility of subclasses being allowed.
        for allowed_type in self._types:
            # Check if the type is correct and if subclasses are allowed
            if not self._allow_subclasses and not issubclass(type_of_value, allowed_type):
                raise TypeError(f"{name} must be of type {allowed_type}")
            # Check if the type is correct and if subclasses are not allowed
            if not issubclass(type_of_value, allowed_type):
                raise TypeError(f"{name} must be of type {allowed_type}")


class Numeric(Typed):
    """
    Numeric executor. This executor checks the type of the value that is being set, making sure that it is a number. The
    definition of a number is defined as conforming to the Number type from the numbers module.
    """
    def __init__(self, **kwargs):
        """
        Initialize the executor. If you want to override the type, you can do so by passing the allowed_types keyword
        argument. Subclasses can be allowed by passing the allow_subclasses keyword argument.
        :param args: Any arguments to pass to the base executor
        :param kwargs: Any keyword arguments to pass to the base executor
        """
        # Set the type to be a Number from the numbers module
        my_type = Number
        if "types" in kwargs.keys():
            my_type = kwargs.pop("types")
        super().__init__(allowed_types=my_type, **kwargs)


class Integer(Typed):
    """
    Integer executor. This executor checks the type of the value that is being set, making sure that it is an integer.
    The definition of an integer is defined as conforming to the int type.
    """
    def __init__(self, **kwargs):
        """
        Initialize the executor. If you want to override the type, you can do so by passing the allowed_types keyword
        argument. Subclasses can be allowed by passing the allow_subclasses keyword argument.
        :param args: Any arguments to pass to the base executor
        :param kwargs: Any keyword arguments to pass to the base executor
        """
        # Set the type to be an int
        my_type = int
        if "types" in kwargs.keys():
            my_type = kwargs.pop("types")
        super().__init__(allowed_types=my_type, **kwargs)


class String(Typed):
    """
    String executor. This executor checks the type of the value that is being set, making sure that it is a string. The
    definition of a string is defined as conforming to the str type.
    """

    def __init__(self, **kwargs):
        """
        Initialize the executor. If you want to override the type, you can do so by passing the allowed_types keyword
        argument. Subclasses can be allowed by passing the allow_subclasses keyword argument.
        :param args: Any arguments to pass to the base executor
        :param kwargs: Any keyword arguments to pass to the base executor
        """
        my_type = str
        if "types" in kwargs.keys():
            my_type = kwargs.pop("types")
        super().__init__(allowed_types=my_type, **kwargs)


class Boolean(Typed):
    """
    Boolean executor. This executor checks the type of the value that is being set, making sure that it is a boolean. The
    definition of a boolean is defined as conforming to the bool type.
    """
    def __init__(self, **kwargs):
        my_type = bool
        if "types" in kwargs.keys():
            my_type = kwargs.pop("types")
        super().__init__(allowed_types=my_type, **kwargs)


class Callable(Typed):
    def __init__(self, **kwargs):
        my_type = Callable
        if "types" in kwargs.keys():
            my_type = kwargs.pop("types")
        super().__init__(allowed_types=my_type, **kwargs)


class LimitedNumber(Numeric):

    def __init__(self, limits: Optional[Tuple[Number, Number]] = None, **kwargs):
        if "limits" in kwargs.keys():
            limits = kwargs.pop("limits")
        super().__init__(**kwargs)
        if limits is None:
            limits = (-float("inf"), float("inf"))
        self._limits = limits
        self._configuration.append(self._check_limits)

    def _check_limits(self, parent, name, value, extra):
        if not self._limits[0] <= value <= self._limits[1]:
            raise ValueError(f"{name} must be between {self._limits[0]} and {self._limits[1]}")

    @property
    def min(self) -> Number:
        return self._limits[0]

    @min.setter
    def min(self, value: Number):
        self._limits = (value, self._limits[1])

    @property
    def max(self) -> Number:
        return self._limits[1]

    @max.setter
    def max(self, value: Number):
        self._limits = (self._limits[0], value)


class Sampler(Executor):
    def __init__(self, sampler: Callable = None, **kwargs):
        if sampler is None:
            raise AttributeError("A valid sampler must be provided.")
        super().__init__(**kwargs)
        self._sampler = sampler
        self._read_modifiers.append(self._get_extension)

    def _get_extension(self, obj, name: str, current_value: Any, extra: Optional[E] = None):
        new_value = self._sampler()
        # We use self.value here as we want to trigger the setters.
        self.value = new_value


class Variable(Executor):
    def __init__(self, constructor: Type[V], **kwargs):
        value, kwargs = self._make_variable(constructor, **kwargs)
        super().__init__(value=value, **kwargs)

    @staticmethod
    def _make_variable(constructor: Type[V], **kwargs ) -> Tuple[V, Dict[str, Any]]:
        constructor_kwargs = {}
        known_kwargs = constructor._descriptors.keys()
        for key in known_kwargs:
            if key in kwargs.keys():
                constructor_kwargs[key] = kwargs.pop(key)
        value = constructor(**constructor_kwargs)
        return value, kwargs

    @property
    def value(self):
        return Executor.value.fget(self)

    @value.setter
    def value(self, new_value):

        this_obj = self.value
        # Replace the object on value
        if issubclass(type(new_value), type(this_obj)):
            Executor.value.fset(self, new_value)
        else:
            try:
                # Replace the actual value of the object. Not the hot-swapping of modifiers...
                executor = this_obj.__params__['value']
                # # There might be the posibility that the `value` has not been initialized yet. In that case, we need to
                # # initialize it.
                # if isinstance(executor.parent, type):
                #     this_obj._attach_generator('value', executor.value)
                #     # Get back the executor
                #     executor = this_obj.__params__['value']
                saved_modifiers = executor._write_modifiers
                executor._write_modifiers = self._write_modifiers + executor._write_modifiers  # We add them to the new object (run first)
                Executor.value.fset(executor, new_value)
            except Exception as e:
                raise ValueError("Cannot set value of this object") from e
            finally:
                # Restore the modifiers
                executor._write_modifiers = saved_modifiers


class ExtendedVariable(Variable):
    def __init__(self, constructor: Type[V], extensions: Union[Type[Executor], List[Type[Executor]]], **kwargs):
        if not isinstance(extensions, list):
            extensions = [extensions]
        initialized_extensions = []
        for extension in extensions:
            sig = signature(extension.__init__)
            all_keys = {n: v.kind for n, v in sig.parameters.items()
                        if n != 'self' and v.kind in [v.KEYWORD_ONLY, v.POSITIONAL_OR_KEYWORD]}
            for key in all_keys.keys():
                if key in kwargs.keys():
                    all_keys[key] = kwargs.pop(key)
                else:
                    raise AttributeError(f"Missing argument {key} for extension {extension}")
            initialized_extensions.append(extension(**all_keys))
        super().__init__(constructor, **kwargs)
        for extension in initialized_extensions:
            self._read_modifiers += extension._read_modifiers
            self._write_modifiers += extension._write_modifiers
            self._configuration += extension._configuration
            self._class_executions += extension._class_executions
            self._executions += extension._executions


class Selector(Executor):
    def __init__(self, *args, choices: List[Any] = None, **kwargs):
        if "choices" in kwargs.keys():
            choices = kwargs.pop("choices")
        super().__init__(*args, **kwargs)
        self._choices = choices
        self._write_modifiers.append(self._set_extension)

    @property
    def choices(self) -> List[Any]:
        return self._choices

    @choices.setter
    def choices(self, new_choices: List[Any]):
        if not self.readonly:
            self._choices = new_choices

    def _set_extension(self, obj, name: str, new_value: Any, extra: Optional[E] = None):
        if new_value not in self._choices:
            raise ValueError(f"{new_value} is not a valid choice")


class Modifier:

    @abc.abstractmethod
    def __call__(self, obj, name: str, value: Any, extra: Optional[E] = None) -> NoReturn:
        pass


class Logger(Modifier):
    def __init__(self, logger: logging.Logger, level: int = logging.WARNING):
        self._logger = logger
        self._level = level
        self._logger.setLevel(level)

    @property
    def level(self) -> int:
        return self._level

    @level.setter
    def level(self, new_level: int):
        self._level = new_level
        self._logger.setLevel(new_level)

    def __call__(self, obj, name: str, value: Any, extra: Optional[E] = None):
        self._logger.warning(f"{obj.__class__.__name__}.{name} set to {value} from {extra.previous_value}")

    def __deepcopy__(self, memodict={}):
        return self
