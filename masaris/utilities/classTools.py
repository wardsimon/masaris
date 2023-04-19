__author__ = "github.com/wardsimon"
__version__ = "0.1.0"


def add_par_to_class(inst, name: str, par) -> None:
    cls = type(inst)
    annotations = getattr(cls, "__annotations__", False)
    if not hasattr(cls, "__perinstance"):
        cls = type(cls.__name__, (cls,), {"__module__": __name__})
        cls.__perinstance = True
        if annotations:
            cls.__annotations__ = annotations
        inst.__old_class__ = inst.__class__
        inst.__class__ = cls

    inst._descriptors[name] = par  # Register with the class
    inst.__params__[name] = par  # Register with the instance

    # Perform reverse registration since __set_name__ is not called automatically
    par.__set_name__(cls, name)

    setattr(cls, name, par)  # Set the attribute on the NEW class
