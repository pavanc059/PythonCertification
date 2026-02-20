#PCPP-32-101 1.1 – Understand and explain the basic terms and programming concepts used in the OOP paradigm
from objects_classes_attributes.pizza import Pizza


if __name__ == "__main__":
    # Essential terminology: class, instance, object, attribute, method, type, instance and class variables, superclasses and subclasses
    print("\n ---Creating first pizza instance as pizza1--- \n")
    pizza1 = Pizza(14, ['pepperoni', 'mushrooms']) # pizza1 is an instance of the Pizza class. Objects are instantiated from classes and stored in memory with their attributes and methods.
    print(f'pizza1 instance describe_pizza method called {pizza1.describe_pizza()}') # describe_pizza is a method of the Pizza class that provides a description of the pizza instance. It uses the instance's attributes to generate the description.
    pizza1.extra_cheese = True # extra_cheese is a property of the Pizza class. 
    print(f'pizza1 instance __dict__ attributes: {pizza1.__dict__}') # __dict__ is a special attribute that contains a dictionary of the instance's attributes and their values. It allows us to see the current state of the instance's attributes.
    # Attributes can be instance variables (specific to each instance) or class variables (shared among all instances). Methods are functions defined within a class that operate on instances of the class.
    # properties are a special type of attribute that allows for controlled access and modification. They can have getter and setter methods to manage the underlying data and ensure that it is accessed and modified in a controlled manner.
    
    print("\n ---Creating another pizza instance--- \n")
    veggie_pizza =  Pizza(14, ["jalapenos","cheese"]) # instantiation and initialization
    veggie_pizza._Pizza__allowed_sizes.append(20) # Access class attribute and motify it (class attribute is modified)
    print(f'veggie_pizza._Pizza__allowed_sizes: {veggie_pizza._Pizza__allowed_sizes}\n') # Access class attribute (class attribute is accessed) using instance._classname__attributename
    veggie_pizza.extra_cheese = True # Setting property method
    veggie_pizza.price = 35 # Setting property method to trigger price calculation
    print(f'dir of veggie_pizza: {dir(veggie_pizza)}\n') # Accessing instance attributes using __dict__
    print(f'veggie_pizza.describe_pizza(): {veggie_pizza.describe_pizza()}\n')
    #veggie_pizza.base_price = 12 # Setting instance attribute
    print(f'veggie_pizza.extra_cheese: {veggie_pizza.extra_cheese}\n') # Accessing property method
    print(f'veggie_pizza.describe_pizza(): {veggie_pizza.describe_pizza()}\n')

    