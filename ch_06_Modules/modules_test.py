
from math import * 
import math # below print will give error if this import is commented


print(dir(math))

from random import choice, sample, randint, randrange, random, seed


seed(0)

for i in range(5):
    print(random())

print(randrange(1), end=' ')
print(randrange(0, 1), end=' ')
print(randrange(0, 1, 1), end=' ')
print(randint(0, 1))

for i in range(10):
    print(randint(1, 10), end=',')

lst = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

print(choice(lst))
print(sample(lst, 5))
print(sample(lst, 10))

from platform import platform, machine, processor, system, version, python_implementation, python_version_tuple

print(platform())
print(platform(1))
print(platform(0, 1))
print(machine())
print(processor())
print(system())
print(version())

print(python_implementation())

for atr in python_version_tuple():
    print(atr)