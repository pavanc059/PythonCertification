# Abstract Classes in Python

Python is considered to be a very flexible programming language, but that doesn’t mean that there are no controls to impose a set of functionalities or an order in a class hierarchy. When you develop a system in a group of programmers, it would be useful to have some means of establishing requirements for classes in matters of interfaces (methods) exposed by each class. 

In Python, an abstract class is a class that cannot be instantiated. Abstract classes are meant to be subclassed, and they typically contain one or more abstract methods. An abstract method is a method that is declared, but contains no implementation. Abstract classes are defined using the `abc` module.

## Defining an Abstract Class

An abstract class should be considered a blueprint for other classes, a kind of contract between a class designer and a programmer:

- The class designer sets requirements regarding methods that must be implemented by just declaring them, but not defining them in detail. Such methods are called abstract methods.
- The programmer has to deliver all method definitions and the completeness would be validated by another, dedicated module. The programmer delivers the method definitions by overriding the method declarations received from the class designer.
- Python has come up with a module which provides the helper class for defining Abstract Base Classes (ABC) and that module name is abc.
- The ABC allows you to mark classes as abstract ones and distinguish which methods of the base abstract class are abstract. A method becomes abstract by being decorated with an @abstractmethod decorator. 

#### Steps for creating abstract class
1) import the abc module;
2) make your base class inherit the helper class ABC, which is delivered by the abc module;
3) decorate abstract methods with @abstractmethod, which is delivered by the abc module.

To define an abstract class in Python, you need to import `ABC` and `abstractmethod` from the `abc` module. Here is an example:

```python
from abc import ABC, abstractmethod

class Animal(ABC): # class Animal(abc.ABC)
    @abstractmethod
    def make_sound(self):
        pass
```

In this example, `Animal` is an abstract class with an abstract method `make_sound`.

## Subclassing an Abstract Class

When you subclass an abstract class, you must implement all of its abstract methods. If you do not, the subclass will also be considered abstract and cannot be instantiated. Here is an example:

```python
class Dog(Animal):
    def make_sound(self):
        return "Bark"

class Cat(Animal):
    def make_sound(self):
        return "Meow"
```

In this example, `Dog` and `Cat` are concrete subclasses of `Animal` that implement the `make_sound` method.

## Using Abstract Classes

Why do we want to use abstract classes?

The very important reason is: we want our code to be polymorphic, so all subclasses have to deliver a set of their own method implementations in order to call them by using common method names.

Furthermore, a class which contains one or more abstract methods is called an abstract class. This means that abstract classes are not limited to containing only abstract methods – some of the methods can already be defined, but if any of the methods is an abstract one, then the class becomes abstract.

Abstract classes are useful when you want to define a common interface for a group of subclasses. They allow you to enforce certain methods to be implemented in the subclasses. Here is an example of how you might use the `Animal` abstract class:

```python
def animal_sound(animal: Animal):
    print(animal.make_sound())

dog = Dog()
cat = Cat()

animal_sound(dog)  # Output: Bark
animal_sound(cat)  # Output: Meow
```

In this example, the `animal_sound` function takes an `Animal` object and calls its `make_sound` method. This demonstrates polymorphism, where the same method call behaves differently depending on the type of the object.

## Summary

- Abstract classes cannot be instantiated.
- Abstract classes are defined using the `ABC` class from the `abc` module.
- Abstract methods are declared using the `@abstractmethod` decorator.
- Subclasses of an abstract class must implement all abstract methods.

Abstract classes are a powerful feature in Python that help you define and enforce a common interface for a group of related classes.
