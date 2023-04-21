__author__ = "github.com/wardsimon"
__version__ = "0.1.0"


from masaris.objects.variables import Descriptor
from masaris.objects.core import Parameterized
from masaris.objects.executors import Variable

d = Descriptor()
print(d)


class A(Parameterized):
    a = Variable(Descriptor, value=9)

    def __init__(self, a=None):
        super().__init__(a=a)

a = A()
a.a = 10
print(a)