__author__ = "github.com/wardsimon"
__version__ = "0.1.0"



def register_graphics(cls, fn):
    setattr(cls, fn.__name__, fn)