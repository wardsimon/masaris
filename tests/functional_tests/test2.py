__author__ = "github.com/wardsimon"
__version__ = "0.1.0"

from masaris.objects.core import Parameterized
from masaris.objects.executors import Integer, String
from masaris.objects.watchers import Watchers


class Test(Parameterized):
    a = Integer(2)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @Watchers.watch(variables=['a'])
    def print(self, *args, **kwargs):
        print(f'{self.a} called from watcher with {args} and {kwargs}')

    @Watchers.depends(variables=['a'])
    def print2(self):
        print(f'{self.a} called from a dependency')
#
# class Test2(Test):
#     b = Integer(3)
#
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#
#
# t = Test(a=10)
# print(f'{t.a} called from main')
# t.a = 5
# print(f'{t.a} called from main')
# tt = Test2(a=10, b=20)
# print(f'{tt.a} called from main')
# tt.a = 5
# print(f'{tt.a} called from main')
# tt.b = 10
# print(f'{tt.b} called from main')


class Test3(Test):
    a = String('Hello')


t = Test3()
print(f'{t.a} called from main')
t.a = 'World'
print(f'{t.a} called from main')