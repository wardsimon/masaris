__author__ = "github.com/wardsimon"
__version__ = "0.1.0"

from .executors import String, Numeric, LimitedNumber, Boolean, Executor
from .core import BaseParameterized
from .watchers import Watchers


class Descriptor(BaseParameterized):
    name = String(value="DefaultDescriptor", visible=False)
    value = Executor()
    units = String(value="", visible=False)
    description = String(value="", visible=False)
    url = String(value="", visible=False)
    display_name = String(value="", visible=False)
    enabled = Boolean(value=True, visible=False)

    def __init__(self, name=None, value=None, units=None, description=None, url=None, display_name=None, enabled=None, **kwargs):
        super().__init__(name=name, value=value, units=units, description=description, url=url, display_name=display_name, enabled=enabled, **kwargs)
        Watchers.register(self, 'name', self._update_display_name)
        Watchers.register(self, 'enabled', self._update_enabled_value)

    def __reduce__(self):
        """
        Make the class picklable. Due to the nature of the dynamic class definitions special measures need to be taken.
        :return: Tuple consisting of how to make the object
        :rtype: tuple
        """
        state = self.encode()
        cls = getattr(self, "__old_class__", self.__class__)
        return cls.from_dict, (state,)

    @property
    def full_value(self):
        return self.value

    @full_value.setter
    def full_value(self, value):
        self.value = value

    def __repr__(self):
        """Return printable representation of a Descriptor/Parameter object."""
        class_name = self.__class__.__name__
        obj_name = self.name
        obj_value = self.value

        if isinstance(obj_value, float):
            obj_value = "{:0.04f}".format(obj_value)
        # obj_units = ""
        # if not self.unit.dimensionless:
        #     obj_units = " {:~P}".format(self.unit)
        obj_units = self.units
        out_str = f"<{class_name} '{obj_name}': {obj_value}{obj_units}>"
        return out_str

    @staticmethod
    def _update_display_name(obj, name, value, extra):
        if obj.display_name == "":
            obj.display_name = value

    @staticmethod
    def _update_enabled_value(obj, name, value, extra):
        obj.pars['value'].enabled = value

    def __copy__(self):
        return self.__class__.from_dict(self.as_dict())
