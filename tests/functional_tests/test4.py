__author__ = "github.com/wardsimon"
__version__ = "0.1.0"


from masaris.objects.variables import Descriptor
from masaris.objects.core import Parameterized
from masaris.objects.executors import Variable, Logger

import logging

FORMAT = '%(asctime)s %(clientip)-15s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.Logger('test')

m = Logger(logger=logger)


class A(Parameterized):
    a = Variable(Descriptor, value=9, write_modifiers=[m], read_modifiers=[m])

    def __init__(self, a=None):
        super().__init__(a=a)

a = A()
a.a = 10
print(a)