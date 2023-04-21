#  SPDX-FileCopyrightText: 2023 easyCore contributors  <core@easyscience.software>
#  SPDX-License-Identifier: BSD-3-Clause
#  © 2021-2023 Contributors to the easyCore project <https://github.com/easyScience/easyCore

from __future__ import annotations

__author__ = "github.com/wardsimon"
__version__ = "0.0.1"

from copy import deepcopy
from typing import Optional, List, Dict, Any, TYPE_CHECKING, TypeVar, Type, NoReturn, Union, Callable
from hashlib import sha1
import json

from masaris.utilities.classTools import add_par_to_class
from masaris.utilities.io.dict import DictSerializer, DataDictSerializer
from masaris.utilities.io.json import jsanitize
from collections import OrderedDict

if TYPE_CHECKING:
    from masaris.utilities.io.template import EC


class ComponentSerializer:
    """
    This is the base class for all easyCore objects and deals with the data conversion to other formats via the `encode`
    and `decode` functions. Shortcuts for dictionary and data dictionary encoding is also present.
    """

    _CORE = True

    def encode(
            self, skip: Optional[List[str]] = None, encoder: Optional[EC] = None, **kwargs
    ) -> Any:
        """
        Use an encoder to covert an easyCore object into another format. Default is to a dictionary using
        `DictSerializer`.
        :param skip: List of field names as strings to skip when forming the encoded object
        :param encoder: The encoder to be used for encoding the data. Default is `DictSerializer`
        :param kwargs: Any additional key word arguments to be passed to the encoder
        :return: encoded object containing all information to reform an easyCore object.
        """

        if encoder is None:
            encoder = DictSerializer
        encoder_obj = encoder()
        return encoder_obj.encode(self, skip=skip, **kwargs)

    @classmethod
    def decode(cls, obj: Any, decoder: Optional[EC] = None) -> Any:
        """
        Re-create an easyCore object from the output of an encoder. The default decoder is `DictSerializer`.
        :param obj: encoded easyCore object
        :param decoder: decoder to be used to reform the easyCore object
        :return: Reformed easyCore object
        """

        if decoder is None:
            decoder = DictSerializer
        return decoder.decode(obj)

    def as_dict(self, skip: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Convert an easyCore object into a full dictionary using `DictSerializer`.
        This is a shortcut for ```obj.encode(encoder=DictSerializer)```
        :param skip: List of field names as strings to skip when forming the dictionary
        :return: encoded object containing all information to reform an easyCore object.
        """

        return self.encode(skip=skip, encoder=DictSerializer)

    @classmethod
    def from_dict(cls, obj_dict: Dict[str, Any]) -> None:
        """
        Re-create an easyCore object from a full encoded dictionary.
        :param obj_dict: dictionary containing the serialized contents (from `DictSerializer`) of an easyCore object
        :return: Reformed easyCore object
        """

        return cls.decode(obj_dict, decoder=DictSerializer)

    def encode_data(
            self, skip: Optional[List[str]] = None, encoder: Optional[EC] = None, **kwargs
    ) -> Any:
        """
        Returns just the data in an easyCore object win the format specified by an encoder.
        :param skip: List of field names as strings to skip when forming the dictionary
        :param encoder: The encoder to be used for encoding the data. Default is `DataDictSerializer`
        :param kwargs: Any additional keywords to pass to the encoder when encoding.
        :return: encoded object containing just the data of an easyCore object.
        """

        if encoder is None:
            encoder = DataDictSerializer
        return self.encode(skip=skip, encoder=encoder, **kwargs)

    def as_data_dict(self, skip: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Returns a dictionary containing just the data of an easyCore object.
        :param skip: List of field names as strings to skip when forming the dictionary.
        :return: dictionary containing just the data of an easyCore object.
        """

        return self.encode(skip=skip, encoder=DataDictSerializer)

    def unsafe_hash(self) -> sha1:
        """
        Returns a hash of the current object. This uses a generic but low
        performance method of converting the object to a dictionary, flattening
        any nested keys, and then performing a hash on the resulting object
        """

        def flatten(obj, seperator="."):
            # Flattens a dictionary

            flat_dict = {}
            for key, value in obj.items():
                if isinstance(value, dict):
                    flat_dict.update(
                        {
                            seperator.join([key, _key]): _value
                            for _key, _value in flatten(value).items()
                        }
                    )
                elif isinstance(value, list):
                    list_dict = {
                        "{}{}{}".format(key, seperator, num): item
                        for num, item in enumerate(value)
                    }
                    flat_dict.update(flatten(list_dict))
                else:
                    flat_dict[key] = value

            return flat_dict

        ordered_keys = sorted(
            flatten(jsanitize(self.as_dict())).items(), key=lambda x: x[0]
        )
        ordered_keys = [item for item in ordered_keys if "@" not in item[0]]
        return sha1(json.dumps(OrderedDict(ordered_keys)).encode("utf-8"))  # nosec


class ExecutorBase:
    """
    Base class for all executors. This class is used to define the interface for all executors.
    This class is not intended to be used directly. Instead, use the `Executor` class which has more functionality.

    The idea of this class is to provide a way to execute an arbitrary number of function when a value is set.
    There are three types of execution:
      - Configuration: This is something which is inherent to the Executor/ExecutorDerrived class. This is typically
      used
        to ensure type checking etc.
      - Class level execution: This is something which is inherent to the class on which the executor is defined.
      This is
        typically used for inner class callbacks. i.e you always want something to run when changing a value in a class.
      - Instance level execution: This is something which is inherent to the instance of the class on which the
      executor is
        defined. This is typically used for outer class callbacks. i.e you want something to run when changing a value
        in something which isn't defined in the class.

    """

    def __init__(self, value: Optional[Any] = None,
                 write_modifiers: Optional[List[Callable]] = None,
                 read_modifiers: Optional[List[Callable]] = None
                 ):
        """
        Initializer for the ExecutorBase class which just sets a value.
        :param value: Any initial value to be set.
        """

        if write_modifiers is None:
            write_modifiers = []
        self._write_modifiers = write_modifiers
        if read_modifiers is None:
            read_modifiers = []
        self._read_modifiers = read_modifiers
        self._executions = []
        self._class_executions = []
        self._configuration = []
        self.previous_value = None
        self._value = value
        self._first = True
        self._default_value = value
        self.name = None
        self.parent = None

    @property
    def value(self) -> Any:
        """
        Internal value of the executor.
        :return: Internal value of the executor.
        """
        # We run all the modifiers
        for modifier in self._read_modifiers:
            modifier(self.parent, self.name, self._value, extra=self)
        return self._value

    @value.setter
    def value(self, new_value: Any) -> NoReturn:
        """
        Sets the value of the executor and runs all the executions.
        :param new_value: New value to be set.
        """
        # The previous value, so it can be restored on error
        previous_value = self.previous_value
        # We set the previous value to the current value
        self.previous_value = self._value
        # We set the INTERNAL current value to the new value
        self._value = new_value

        # We run all the modifiers
        for modifier in self._write_modifiers:
            modifier(self.parent, self.name, new_value, extra=self)

        # We run all the executions
        try:
            # First we execute everything defined in the configuration
            for config_executor in self._configuration:
                config_executor(self.parent, self.name, new_value, extra=self)
            # Then we execute the class level executions i.e. decorators attached to the class.
            for class_executor in self._class_executions:
                class_executor(self.parent, self.name, new_value, extra=self)
            # Finally we execute the executions attached to the instance by the user.
            for execution in self._executions:
                execution(self.parent, self.name, new_value, extra=self)
        except Exception as e:
            # If there is an error, we restore the previous value
            self._value = self.previous_value
            self.previous_value = previous_value
            raise e
        # If we get here, we set the first flag to false
        self._first = False

    @property
    def default(self) -> bool:
        """
        A check to see if the Executor value has been set explicitly.
        :return: Check to see if the Executor value has been set explicitly.
        """
        return self._first

    @property
    def default_value(self) -> Any:
        """
        The default value of the executor.
        :return: Default value of the executor.
        """
        return self._default_value


# Type hinting for the ExecutorBase class and its subclasses
E = TypeVar("E", bound=ExecutorBase)


class BaseParameterized(ComponentSerializer):
    """
    Base class for all parameterized objects. This class is used to define the interface for all parameterized objects.
    """

    def __init__(self, **kwargs):
        self.__params__ = {}
        for name, value in self._descriptors.items():
            if name in kwargs:
                this_value = kwargs.pop(name)
                if this_value is None:
                    self.__params__[name] = value
                    continue
                self._attach_generator(name, this_value)
            else:
                self.__params__[name] = value
        if len(kwargs) > 0:
            for key, value in kwargs.items():
                setattr(self, key, value)
            raise Warning(f"Parameters {kwargs} not found in {self.__class__.__name__}")

    def __getattribute__(self, name: str) -> Any:
        # This might have the problem that it will not work for the first time. This is due to instantiation order. Boo!
        return super().__getattribute__(name)

    def __setattr__(self, key: str, value: Any) -> NoReturn:
        t_ = type(value)
        if key in self._descriptors and self._descriptors[key] == self.__params__[key]:
            self._attach_generator(key, value)
            return
        if key not in self._descriptors and issubclass(t_, Parameterized):
            from masaris.objects.executors import Executor
            self.attachPar(key, Executor(value=value))
            raise Warning(f"Parameter {key} not found in {self.__class__.__name__}, but added")
        super().__setattr__(key, value)

    def _attach_generator(self, name: str, value: Any) -> NoReturn:
        executor = deepcopy(self._descriptors[name])
        executor._first = False  # Set it to be NOT the default value
        executor.parent = self
        executor._default_value = self._descriptors[name].value
        self.__params__[name] = executor
        executor.value = value

    @property
    def pars(self) -> Dict[str, E]:
        return self.__params__

    @property
    def parameters(self) -> List[E]:
        mine = list(self.__params__.items())
        re = []
        for item in mine:
            if not item[1]._visible:
                continue
            re.append(item[1])
            if issubclass(type(item[1].value), BaseParameterized):
                re += item[1].value.parameters
        return re


Pcls = Type[BaseParameterized]
Pobj = TypeVar("Pobj", bound=BaseParameterized)


class Parameterized(BaseParameterized):

    @property
    def class_parameters(self) -> List[E]:
        return self._descriptors

    def attach_parameter(self, name: str, par: Union[Pobj, E]):
        add_par_to_class(self, name, par)
