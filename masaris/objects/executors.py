__author__ = "github.com/wardsimon"
__version__ = "0.1.0"

from copy import deepcopy

from .core import ExecutorBase, Parameterized

from typing import Optional, Tuple, Union
from numbers import Number



class MyDict(dict):
    pass


class Executor(ExecutorBase):
    def __init__(self, *args, readonly=False, visible=True, inherit_watchers=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._readonly = readonly
        self._visible = visible
        self._inherit_watchers = inherit_watchers

    def __set_name__(self, owner, name):
        self.name = name
        self.parent = owner
        descriptors = getattr(owner, "_descriptors", None)
        if descriptors is not None:
            if getattr(descriptors, "owner_class", None) != owner.__qualname__:
                owner._descriptors = MyDict(**descriptors)
                setattr(owner._descriptors, "owner_class", owner.__qualname__)
            # Check to see if there is a class watcher...
            previous_executor = owner._descriptors.get(self.name, None)
            if previous_executor is not None:
                if hasattr(previous_executor, "_class_executions") and len(previous_executor._class_executions) > 0 and self._inherit_watchers:
                    self._class_executions = deepcopy(previous_executor._class_executions)
            owner._descriptors[name] = self
        else:
            setattr(owner, "_descriptors", MyDict())
            setattr(owner._descriptors, "owner_class", owner.__qualname__)
            owner._descriptors[name] = self

    def __get__(self, obj, objtype=None):
        if not hasattr(obj, "__params__"):
            return self.value
        return obj.__params__.get(self.name).value

    def __set__(self, obj, value):
        if self._readonly:
            raise AttributeError("Cannot set a readonly attribute")
        if not hasattr(obj, "__params__"):
            raise AttributeError("Class does not have __params__")
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


class Typed(Executor):
    def __init__(self, *args, types: Union[type, Tuple[type]] = None, allow_subclasses: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        if types is None:
            types = object

        if not isinstance(types, tuple):
            types = (types,)
        self._types = types
        self._configuration.append(self._check_type)
        self._kwargs["types"] = types
        self._kwargs["allow_subclasses"] = allow_subclasses

    def _check_type(self, parent, name, value, extra):
        tpvalue = type(value)
        for allowed_type in self._types:
            if not self._kwargs["allow_subclasses"] and tpvalue != allowed_type:
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
        super().__init__(*args, types=Callable, **kwargs)
        self._kwargs.pop("types")


class LimitedNumber(Numeric):

    def __init__(self, *args, limits: Optional[Tuple[Number, Number]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        if limits is None:
            limits = (-float("inf"), float("inf"))
        self._limits = limits
        self._configuration.append(self._check_limits)
        self._kwargs["limits"] = limits

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
        self._kwargs["sampler"] = sampler

    @property
    def value(self):
        new_value = self._sampler()
        Executor.value.fset(self, new_value)
        return new_value
