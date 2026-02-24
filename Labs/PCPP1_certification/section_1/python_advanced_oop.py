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

    print(f"\n_____________ Creating Iterator and iterable using special functions __________\n")

    #Iterable example 
    from special_functions.iterators_iterables import Person, PersonList, Fibonacci, PersonIterable

    for i in Fibonacci(50):
        print(i)

    persons_iterator = PersonList(Person("Joy", 35), Person("Kyle", 34), Person("Alison",20), Person("Jacob", 30))

    for p in persons_iterator:
        print(p)

    persons_iterable = PersonIterable(Person("Neal", 35), Person("Sony", 34), Person("Gary",20), Person("Ted", 30)) # iterable doesn't implement next method

    for p in persons_iterable:
        print(p)

    # print(persons_iterable[0:2]) this would give error because persons_iterable is not a sequence or mapping

    print("\n_____________ Creating sequence and mapping using special functions __________\n")
    
    from special_functions.sequences_mappings import OnlineBooksCatalog

    online_books = OnlineBooksCatalog()
    print(online_books[0:10])
    print(f'Contains check : {"Don Quixote" in online_books}')
    print(f'Length of online_books: {len(online_books)}')
    
    print("\n_____________ Class attributes and Properties __________\n")
    
    from objects_classes_attributes.getters_setters import Car
    car1 = Car("Toyota", "Camry")
    print(f'car1 make: {car1.get_make()}') # Accessing make
    print(f'car1 model: {car1.get_model()}') # Accessing model
    car1.set_make("Honda") # Modifying make
    car1.set_model("Civic") # Modifying model
    print(f'car1 make after modification: {car1.get_make()}')
    print(f'car1 model after modification: {car1.get_model()}')

    from objects_classes_attributes.getters_setters import Vehicle, LandVehicle
    vehicle1 = Vehicle("Car", 4)
    print(f'vehicle1 type: {vehicle1.type}') # Accessing type using property
    print(f'vehicle1 number of wheels: {vehicle1.number_of_wheels}') # Accessing number_of_wheels using property
    vehicle1.type = "Truck" # Modifying type using property setter
    vehicle1.number_of_wheels = 6 # Modifying number_of_wheels using property
    print(f'vehicle1 type after modification: {vehicle1.type}')
    print(f'vehicle1 number of wheels after modification: {vehicle1.number_of_wheels}')

    land_vehicle1 = LandVehicle("SUV", 4, "Off-road")
    print(f'land_vehicle1 type: {land_vehicle1.type}') # Accessing type
    print(f'land_vehicle1 terrain: {land_vehicle1.terrain}') # Accessing terrain
    #land_vehicle1.type = "Crossover" # Modifying type using property setter
    #print(f'land_vehicle1 type after modification: {land_vehicle1.type}')
    #Above statement would give error because terrain property doesn't have setter method defined.
    # even type setter is part for parent it is not accessible in child class because it is overridden by type property in child class which doesn't have setter method defined. 
    # This is an example of how properties can control access to attributes and how inheritance can affect property access.
    # Traceback (most recent call last):
    # land_vehicle1.type = "Crossover" # Modifying type using property setter
    # ^^^^^^^^^^^^^^^^^^
    # AttributeError: property 'type' of 'LandVehicle' object has no setter

    print('\n Using descriptors to control access to attributes \n')
    from objects_classes_attributes.getters_setters import PizzaSizes, Shape, Points, SquareOfNumbers, CachedFunctionResults

    pizza1 = PizzaSizes(14) # Creating pizza instance with size 25
    print(f'Pizza size: {pizza1.size}') # Accessing size using descriptor
    pizza1.size = 20 # Modifying size using descriptor setter

    circle = Shape("Circle", 1) # Creating shape instance with shape "Circle"
    print(f'Shape: {circle.name}, Radius: {circle.no_of_sides}') # Accessing shape and radius using descriptor
    triangle = Shape("Triangle", 3) # Creating shape instance with shape "Triangle"
    print(f'Shape: {triangle.name}, Sides: {triangle.no_of_sides}') #
    triangle.no_of_sides = 4 # Modifying sides using descriptor setter
    print(f'Shape: {triangle.name}, Sides after modification: {triangle.no_of_sides}') # Accessing sides after modification using descriptor

    point1 = Points(10, 20) # Creating point instance with x=10, y=20
    print(f'Point: ({point1.get_x()}, {point1.get_y()})') # Accessing x and y using getter methods
    point1.x = 15 # Modifying x using setter method
    point1.y = 25 # Modifying y using setter method 
    print(f'Point after modification: ({point1.x}, {point1.y})') # Accessing x and y after modification using property getters

    squares = SquareOfNumbers(5) # Creating instance of SquareOfNumbers with size 5
    print(f'Squares of numbers from 0 to 4: {squares.number}') # Accessing squares using cached_property
    squares = SquareOfNumbers(5)
    print(f'Squares of numbers from 0 to 5 (cached): {squares.number}') # Accessing squares again to demonstrate caching (cached value is returned without recomputation) 
    squares.number = 10 # 
    print(f'Squares of numbers from 0 to 10 (cached): {squares.number}') # setting number to 10 doesn't cause recomputation because cached_property doesn't have setter method defined, it will return the cached value of squares from 0 to 5 instead of recalculating squares from 0 to 10.
    
    def expensive_computation(x):
        print(f'Performing expensive computation for {x}...')
        return x * x

    cached_value = CachedFunctionResults(expensive_computation) # Creating instance of CachedFunctionResults with value 10
    print(f'Cached value: {cached_value(10)}') # Accessing cached value using cached
    print(f'Cached value: {cached_value(10)}')
    print(f'Cached value: {cached_value(100)}')

############################# PCPP-32-101 1.5 – Design, build, and use Python static and class methods #############################
    print("\n_____________ PCPP-32-101 1.5 – Design, build, and use Python static and class methods __________\n")
    
    from objects_classes_attributes.class_static_methods import DaysInAWeek, Employee

    print(f'Day in a week enum: {DaysInAWeek.Monday}, value: {DaysInAWeek.Monday.value} and name: {DaysInAWeek.Monday.name}') # Accessing enum member and its value``

    print(f'Is Monday a workday? {Employee.is_workday("Monday")}')
    print(f'Is Saturday a workday? {Employee.is_workday("tuesday")}') 
    print(f'Is Monday a workday? {Employee.is_workday(0)}')

    emp1 = Employee("John", "Doe", 50000)
    print(f'Employee full name: {emp1.fullname()}') # Accessing instance method
    print(f'Employee raise amount before update: {emp1.raise_amount}') # Accessing
    Employee.update_raise_amount(1.05) # Updating class variable using class method
    emp2 = Employee("Jane", "Smith", 60000)
    print(f'Employee raise amount after update: {emp1.raise_amount}') # Accessing updated class variable using instance
    print(f'Employee raise amount for new instance: {emp2.raise_amount}') # Accessing updated class variable using new instance
    emp1.raise_amount = 1.06 # Modifying class variable using instance (this creates an instance variable that shadows the class variable for emp1)
    print(f'Employee raise amount for emp1 after modification: {emp1.raise_amount}') # Accessing modified raise_amount for emp1 (instance variable)
    print(f'Employee raise amount for emp2 after emp1 modification: {emp2.raise_amount}') # Accessing raise_amount for emp2 (still refers to class variable)
    emp_str = "Alice-Wonderland-70000"
    emp3 = Employee.from_string(emp_str) # Creating new instance using class method from_string
    print(f'Employee 3 full name: {emp3.fullname()}') # Accessing instance method for emp3
    print(f'Employee 3 raise amount: {emp3.raise_amount}') # Accessing class variable for emp3 (inherits from Employee class)



