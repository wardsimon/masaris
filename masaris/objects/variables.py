
from __future__ import annotations

__author__ = "github.com/wardsimon"
__version__ = "0.1.0"

import numpy as np
import sys

from numbers import Number
from typing import Union, Dict, Any, Tuple, Optional, Callable, TypeVar, TYPE_CHECKING, NoReturn

if sys.version_info >= (3, 11):
    from typing import Self
else:
    Self = TypeVar('Self', bound='Descriptor')

from masaris import ureg
from .executors import String, Numeric, LimitedNumber, Boolean, Executor
from .core import BaseParameterized
from .watchers import Watchers

if TYPE_CHECKING:
    from .core import E


class Descriptor(BaseParameterized):
    name = String(value="DefaultDescriptor", visible=False)
    value = Executor()
    units = String(value="", visible=False)
    description = String(value="", visible=False)
    url = String(value="", visible=False)
    display_name = String(value="", visible=False)
    enabled = Boolean(value=True, visible=False)

    def __init__(self, name: Optional[str] = None, value: Optional[Any] = None,
                 units: Optional[str] = None, description: Optional[str] = None,
                 url: Optional[str] = None, display_name: Optional[str] = None,
                 enabled: Optional[bool] = True, **kwargs):
        self._unit_cache = ureg(units).units
        if not self._unit_cache.dimensionless:
            units = str(self._unit_cache)
        super().__init__(name=name, value=value, units=units, description=description,
                         url=url, display_name=display_name, enabled=enabled, **kwargs)

    def __copy__(self) -> Self:
        return self.__class__.from_dict(self.as_dict())

    def __reduce__(self) -> Tuple[Callable, Tuple[Dict[str, Any]]]:
        """
        Make the class picklable. Due to the nature of the dynamic class definitions special measures need to be taken.
        :return: Tuple consisting of how to make the object and the arguments to make it.
        """
        state = self.encode()
        cls = getattr(self, "__old_class__", self.__class__)
        return cls.from_dict, (state,)

    def __repr__(self) -> str:
        """Return printable representation of a Descriptor/Parameter object."""

        class_name = self.__class__.__name__
        obj_name = self.name
        obj_value = self.value

        obj_units = ""
        if not self._unit_cache.dimensionless:
            obj_units = " {:~P}".format(self._unit_cache)
        out_str = f"<{class_name} '{obj_name}': {obj_value}{obj_units}>"
        return out_str

    @property
    def full_value(self) -> ureg.Quantity:
        return self.value * self._unit_cache

    @full_value.setter
    def full_value(self, value: Union[Number, ureg.Quantity]) -> NoReturn:
        old_unit = self._unit_cache
        new_unit = None
        if hasattr(value, "magnitude"):
            new_unit = value.units
            value = value.magnitude
            if hasattr(value, "nominal_value"):
                value = value.nominal_value
            if str(new_unit) == str(old_unit):
                new_unit = None
        self.value = value
        if new_unit is not None:
            self._unit_cache = ureg(str(new_unit)).units
            self.units = str(new_unit)

    @Watchers.watch(['name'])
    def _update_display_name(self: Self, name: str, value: Any, extra: E) -> NoReturn:
        if self.display_name == "":
            self.display_name = value

    @Watchers.watch(['value'])
    def _update_enabled(self: Self, name: str, value: Any, extra: E) -> NoReturn:
        self.pars[name].enabled = value

    @Watchers.watch(['units'])
    def _update_unit_cache(self: Self, name: str, value: Any, extra: E) -> NoReturn:
        if not self._unit_cache.dimensionless:
            old_full = self.full_value
            new_full = old_full.to(value)
            tmp_value = new_full.magnitude
            if hasattr(tmp_value, "nominal_value"):
                tmp_value = tmp_value.nominal_value
            self.value = tmp_value
            self._unit_cache = new_full.units
        else:
            self._unit_cache = ureg(value).units


V = TypeVar("V", bound=Descriptor)


class Parameter(Descriptor):
    value = LimitedNumber(value=0)
    error = Numeric(value=0, visible=False)
    min = Numeric(value=-np.Inf, visible=False)
    max = Numeric(value=np.Inf, visible=False)
    fixed = Boolean(value=False, visible=False)

    def __init__(self, name: Optional[str] = None, value: Optional[Number] = None,
                 error: Optional[Any] = None, min: Optional[Number] = None, max: Optional[Number] = None,
                 fixed: Optional[bool] = False, units: Optional[str] = None, description: Optional[str] = None,
                 url: Optional[str] = None, display_name: Optional[str] = None,
                 enabled: Optional[bool] = True, **kwargs):
        super().__init__(name=name, value=value, error=error, min=min, max=max,
                         fixed=fixed, units=units, description=description, url=url,
                         display_name=display_name, enabled=enabled, **kwargs)
        self._update_limits('min', self.min, {})
        self._update_limits('max', self.max, {})

    @Watchers.watch(['min', 'max'])
    def _update_limits(self: Self, name: str, value: Any, extra: Dict[str, Any]) -> NoReturn:
        if name == 'min':
            self.pars['value'].min = value
        elif name == 'max':
            self.pars['value'].max = value

    @property
    def full_value(self) -> ureg.Measurement:
        return super().full_value.plus_minus(self.error)

    @full_value.setter
    def full_value(self, value: Union[Number, ureg.Quantity, ureg.Measurement]) -> NoReturn:
        Descriptor.full_value.fset(self, value)
        if hasattr(value, 'error'):
            error = value.error.magnitude
            self.error = error
