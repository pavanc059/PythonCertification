# Encapsulation in Python

Encapsulation is one of the fundamental concepts in object-oriented programming (OOP). It describes the idea of wrapping data and the methods that work on data within one unit, e.g., a class in Python.

- Encapsulation is used to hide the attributes inside a class like in a capsule, preventing unauthorized parties' direct access to them. Publicly accessible methods are provided in the class to access the values, and other objects call those methods to retrieve and modify the values within the object. This can be a way to enforce a certain amount of privacy for the attributes.
- Python introduces the concept of properties that act like proxies to encapsulated attributes.

This concept has some interesting features:
  - the code calling the proxy methods might not realize if it is "talking" to the real attributes or to the methods controlling access to the attributes;
  - in Python, you can change your class implementation from a class that allows simple and direct access to attributes to a class that fully controls access to the attributes, and what is most important –consumer implementation does not have to be changed; by consumer we understand someone or something (it could be a legacy code) that makes use of your objects.

## Key Points

- **Private Attributes**: In Python, we use underscores to indicate private attributes. A single underscore `_` suggests that the attribute is intended for internal use, while a double underscore `__` makes the attribute name mangled to avoid accidental access.

- **Getter and Setter Methods**: These methods are used to access and update the value of private attributes.

## Access control

Python allows you to control access to attributes with the built-in property() function and corresponding decorator @property. 

This decorator plays a very important role:
  - it designates a method which will be called automatically when another object wants to read the encapsulated attribute value;
  - the name of the designated method will be used as the name of the instance attribute corresponding to the encapsulated attribute;
  - it should be defined before the method responsible for setting the value of the encapsulated attribute, and before the method responsible for deleting the encapsulated attribute.


## Example

```python
class TankError(Exception):
    pass


class Tank:
    def __init__(self, capacity):
        self.capacity = capacity
        self.__level = 0

    @property
    def level(self):
        return self.__level

    @level.setter
    def level(self, amount):
        if amount > 0:
            # fueling
            if amount <= self.capacity:
                self.__level = amount
            else:
                raise TankError('Too much liquid in the tank')
        elif amount < 0:
            raise TankError('Not possible to set negative liquid level')

    @level.deleter
    def level(self):
        if self.__level > 0:
            print('It is good to remember to sanitize the remains from the tank!')
        self.__level = None
```
- We see that every Tank class object has a __level attribute, and the class delivers the methods responsible for handling access to that attribute.

```python
class Example:
    def __init__(self, value):
        self.__value = value  # private attribute

    def get_value(self):
        return self.__value

    def set_value(self, value):
        self.__value = value

# Usage
obj = Example(10)
print(obj.get_value())  # Output: 10
obj.set_value(20)
print(obj.get_value())  # Output: 20
```

In this example, `__value` is a private attribute, and we use `get_value` and `set_value` methods to access and modify it.

## Benefits of Encapsulation

- **Control**: Encapsulation allows control over the data by restricting direct access to it.
- **Security**: It helps in protecting the data from unauthorized access and modification.
- **Flexibility**: It provides flexibility to change the implementation details without affecting the external code.

Encapsulation is a powerful feature that helps in building robust and maintainable code.