from __future__ import annotations

import abc
import logging

_author__ = "github.com/wardsimon"
__version__ = "0.1.0"

from copy import deepcopy
from .core import ExecutorBase, Parameterized
from typing import Optional, Tuple, Union, TYPE_CHECKING, Type, Any, List, NoReturn
from numbers import Number

if TYPE_CHECKING:
    from .variables import V
    from .core import Pcls, Pobj, E


class MyDict(dict):
    """A dictionary that allows you to set attributes on it."""
    pass


class Executor(ExecutorBase):
    """A class that allows you to define a variable that can be watched and executed on change."""
    def __init__(self, *args,
                 readonly: bool = False, visible: bool = True, inherit_watchers: bool = True, allow_none: bool = True,
                 read_modifiers: Optional[List[Callable]] = None, write_modifiers: Optional[List[Callable]] = None, **kwargs):
        """

        :param args: Arguments to pass to the base executor
        :param readonly: Can the value of the variable be changed?
        :param visible: Will the variable be visible in the list of parameters?
        :param inherit_watchers: Should the watchers be inherited from the parent class?
        :param allow_none: Can the value be None?
        :param kwargs: Key word arguments to pass to the base executor
        """
        super().__init__(*args, read_modifiers=read_modifiers, write_modifiers=write_modifiers, **kwargs)
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
        return self._readonly

    @readonly.setter
    def readonly(self, value: bool):
        self._readonly = value

    @property
    def allow_none(self) -> bool:
        return self._allow_none

    @allow_none.setter
    def allow_none(self, value: bool):
        self._allow_none = value


class Typed(Executor):
    def __init__(self, *args, types: Union[type, Tuple[type]] = None, allow_subclasses: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        if types is None:
            types = object
        if not isinstance(types, tuple):
            types = (types,)
        self._types = types
        self._allow_subclasses = allow_subclasses
        self._configuration.append(self._check_type)

    def _check_type(self, parent, name, value, extra):
        tpvalue = type(value)
        for allowed_type in self._types:
            if not self._allow_subclasses and not issubclass(tpvalue, allowed_type):
                raise TypeError(f"{name} must be of type {allowed_type}")
            if not issubclass(tpvalue, allowed_type):
                raise TypeError(f"{name} must be of type {allowed_type}")


class Numeric(Typed):
    def __init__(self, *args, **kwargs):
        my_type = Number
        if "types" in kwargs.keys():
            my_type = kwargs.pop("types")
        super().__init__(*args, types=my_type, **kwargs)


class Integer(Typed):
    def __init__(self, *args, **kwargs):
        my_type = int
        if "types" in kwargs.keys():
            my_type = kwargs.pop("types")
        super().__init__(*args, types=my_type, **kwargs)


class String(Typed):
    def __init__(self, *args, **kwargs):
        my_type = str
        if "types" in kwargs.keys():
            my_type = kwargs.pop("types")
        super().__init__(*args, types=my_type, **kwargs)


class Boolean(Typed):
    def __init__(self, *args, **kwargs):
        my_type = bool
        if "types" in kwargs.keys():
            my_type = kwargs.pop("types")
        super().__init__(*args, types=my_type, **kwargs)


class Callable(Typed):
    def __init__(self, *args, **kwargs):
        my_type = Callable
        if "types" in kwargs.keys():
            my_type = kwargs.pop("types")
        super().__init__(*args, types=my_type, **kwargs)


class LimitedNumber(Numeric):

    def __init__(self, *args, limits: Optional[Tuple[Number, Number]] = None, **kwargs):
        if "limits" in kwargs.keys():
            limits = kwargs.pop("limits")
        super().__init__(*args, **kwargs)
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
    def __init__(self, *args, sampler: Callable = None, **kwargs):
        if "sampler" in kwargs.keys():
            sampler = kwargs.pop("sampler")
        super().__init__(*args, **kwargs)
        self._sampler = sampler

    @property
    def value(self):
        new_value = self._sampler()
        Executor.value.fset(self, new_value)
        return new_value


class Variable(Executor):
    def __init__(self, constructor: Type[V], **kwargs):
        constructor_kwargs = {}
        known_kwargs = constructor._descriptors.keys()
        for key in known_kwargs:
            if key in kwargs.keys():
                constructor_kwargs[key] = kwargs.pop(key)
        value = constructor(**constructor_kwargs)
        super().__init__(value, **kwargs)

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
                saved_modifiers = executor._write_modifiers
                executor._write_modifiers = self._write_modifiers + executor._write_modifiers  # We add them to the new object (run first)
                Executor.value.fset(executor, new_value)
            except Exception as e:
                raise ValueError("Cannot set value of this object") from e
            finally:
                # Restore the modifiers
                executor._write_modifiers = saved_modifiers


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
