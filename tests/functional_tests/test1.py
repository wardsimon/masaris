__author__ = "github.com/wardsimon"
__version__ = "0.1.0"

from masaris.objects.core import Parameterized
from masaris.objects.executors import Executor
from masaris.objects.watchers import Watchers

class MyTest(Parameterized):
    a = Executor(value=9)

    def __init__(self, a):
        super().__init__(a=a)


class F(Parameterized):
    b = Executor()

    def __init__(self, b=None, **kwargs):
        super().__init__(b=b, **kwargs)


class FF(F):
    c = Executor()

    def __init__(self, b, c):
        super().__init__(b=b, c=c)


t = MyTest(1)
tt = MyTest(11)
f = MyTest(F(101))
ff = MyTest(FF(101, 102))
print(t.a, tt.a, f.a)

print(ff.parameters)


def print_a(obj, name, value, extra=None):
    print(f"Value of {name} is {value}. Previous value was {extra.previous_value}")


Watchers.register(t, "a", print_a)
Watchers.register(tt, "a", print_a)

t.a = 2
tt.a = 22
f.a = F(202)
print(t.a, tt.a, f.a)
f.b = "Hey"
try:
    f.c = F(303)
except Warning as e:
    print(e)
print(f.a, f.b, f.c)
