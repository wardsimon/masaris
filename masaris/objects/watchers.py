__author__ = "github.com/wardsimon"
__version__ = "0.1.0"

from functools import partial
from typing import List


class Watchers:

    @staticmethod
    def watch(variables: List[str]):
        watcher = partial(Watcher, variables=variables)
        return watcher

    @staticmethod
    def register(instance, variable, callable_function):
        parameters = getattr(instance, '__params__', None)
        if parameters is None:
            raise AttributeError("Instance has not been initialised")
        variable = parameters.get(variable, None)
        if variable is None:
            raise AttributeError("Variable does not exist")
        variable._executions.append(callable_function)


class Watcher:

    def __init__(self, fget, variables: List[str]):
        self.fget = fget
        self.variables = variables

    def __set_name__(self, owner, name):
        class_descriptors = getattr(owner, "_descriptors", None)
        if class_descriptors is not None:
            for par_name in self.variables:
                executor = class_descriptors.get(par_name, None)
                if executor is not None:
                    executor._class_executions.append(self.fget)
        self.name = name

    def __get__(self, instance, owner):
        return partial(self.fget, instance)

    def __set__(self, instance, value):
        raise AttributeError("Cannot set a watcher")

