#PCPP-32-101 1.1 – Understand and explain the basic terms and programming concepts used in the OOP paradigm
from objects_classes_attributes.pizza import Pizza


if __name__ == "__main__":
    # Essential terminology: class, instance, object, attribute, method, type, instance and class variables, superclasses and subclasses

    pizza1 = Pizza(14, ['pepperoni', 'mushrooms']) # pizza1 is an instance of the Pizza class. Objects are instantiated from classes and stored in memory with their attributes and methods.
    print(pizza1.describe_pizza()) # describe_pizza is a method of the Pizza class that provides a description of the pizza instance. It uses the instance's attributes to generate the description.
    pizza1.extra_cheese = True # extra_cheese is a property of the Pizza class. 
    print(pizza1.__dict__) # __dict__ is a special attribute that contains a dictionary of the instance's attributes and their values. It allows us to see the current state of the instance's attributes.
    # Attributes can be instance variables (specific to each instance) or class variables (shared among all instances). Methods are functions defined within a class that operate on instances of the class.
    # properties are a special type of attribute that allows for controlled access and modification. They can have getter and setter methods to manage the underlying data and ensure that it is accessed and modified in a controlled manner.


    