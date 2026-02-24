# using setter and methods set_text() and get_text()
# using property decorator to create getter and setter methods for a class attribute. This allows for controlled access and modification of the attribute while still providing a simple interface for users of the class.
# Using descriptor protocol to create a custom descriptor class that manages the access and modification of an attribute. This allows for more advanced control over how the attribute is accessed and modified, such as adding validation or logging.
# Using __getattr__ and __setattr__ magic methods to intercept attribute access and modification. This allows for dynamic handling of attributes, such as creating attributes on the fly or implementing custom behavior when attributes are accessed or modified.
# using property() function to create a property that manages the access and modification of an attribute. This allows for a more concise and readable way to define getter and setter methods for an attribute.
# property(fget=None, fset=None, fdel=None, doc=None) is a built-in function that creates a property object in Python. 
#   It allows you to define getter, setter, and deleter methods for an attribute in a class, providing a way to control access and modification of that attribute.
#   https://docs.python.org/3/howto/descriptor.html#properties
# functools import cached_property is a decorator that transforms a method of a class into a property whose value is computed once and then cached as a normal attribute for the life of the instance. This can be useful for expensive computations that you want to avoid repeating.
# functools import cache is a decorator that transforms a function into a memoized function, which caches the results of function calls and 
#       returns the cached result when the same inputs occur again. This can be useful for optimizing performance by avoiding redundant calculations.

class Car:
    '''A simple Car class with getter and setter methods for make and model attributes.'''
    def __init__(self, make, model):
        self._make = make
        self._model = model

    def get_make(self):
        return self._make
    
    def set_make(self, value):
        self._make = value

    def get_model(self):
        return self._model
    
    def set_model(self, value):
        self._model = value

class Vehicle:
    '''A simple Vehicle class with getter and setter methods for make and model attributes.'''
    def __init__(self, type, number_of_wheels):
        self._type = type
        self._number_of_wheels = number_of_wheels

    @property
    def type(self):
        return self._type
    
    @type.setter
    def type(self, value):
        self._type = value

    @property
    def number_of_wheels(self):
        return self._number_of_wheels
    
    @number_of_wheels.setter
    def number_of_wheels(self, value):
        self._number_of_wheels = value
        return self._number_of_wheels
    
class LandVehicle(Vehicle):
    '''A simple LandVehicle class that inherits from Vehicle class.'''
    def __init__(self, type, number_of_wheels, terrain):
        super().__init__(type, number_of_wheels)
        self._terrain = terrain

    @property
    def type(self):
        return self._type

    @property
    def terrain(self):
        return self._terrain
    
    @terrain.setter
    def terrain(self, value):
        self._terrain = value


class AllowedValue:
    def __init__(self, name):
        self.name = name

    def __get__(self, instance, owner):
        return instance.__dict__.get(self.name)

    def __set__(self, instance, value):
        if not isinstance(value, int) or value not in (12, 14, 16, 20):
            raise ValueError(f"{self.name} must be one of (12, 14, 16, 20)")
        instance.__dict__[self.name] = value

class PizzaSizes:
    size = AllowedValue("size")

    def __init__(self, size):
        self.size = size
  
class Shape:
    def __init__(self, name, no_of_sides):
        self.name = name
        self.no_of_sides = no_of_sides 

    def __getattr__(self, name):
        self.__dict__[name] = f"{name} is not defined, but it has been created dynamically"
        return self.__dict__[name]

    def __setattr__(self, name, value):
        if name == "no_of_sides" and (not isinstance(value, int) or value < 0):
            raise ValueError("no_of_sides must be a non-negative integer")
        self.__dict__[name] = value

class Points:
    def __init__(self, x, y):
        self._x = x
        self._y = y

    def get_x(self):
        return self._x
    
    def set_x(self, value):
        self._x = value

    def get_y(self):
        return self._y
    
    def set_y(self, value):
        self._y = value

    property(fget=get_x, fset=set_x, fdel=None, doc="The x coordinate of the point")
    property(fget=get_y, fset=set_y, fdel=None, doc="The y coordinate of the point")

from functools import cached_property, cache
from time import sleep
class SquareOfNumbers:
    def __init__(self, number):
        self._number = number

    @cached_property
    def number(self):
        print("Calculating square...")
        sleep(1) # Simulating an expensive computation
        return self._number ** 2    
    

class CachedFunctionResults:
    def __init__(self, func):
        self.func = func
        self.cache = {}

    @cache
    def __call__(self, *args):
        sleep(3) # Simulating an expensive computation
        return self.func(*args)
       

