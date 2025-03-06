# Composition vs Inheritance



## Composition

Composition is a design principle where a class is composed of one or more objects from other classes, allowing for complex functionality by combining simple objects. It promotes code reuse and flexibility.

- Composition projects a class as a container (called a composite) able to store and use other objects (derived from other classes) where each of the objects implements a part of a desired class's behavior. It’s worth mentioning that blocks are loosely coupled with the composite, and those blocks could be exchanged any time, even during program runtime.

### Example

```python
class Engine:
    def start(self):
        print("Engine started")

class Car:
    def __init__(self, engine):
        self.engine = engine

    def start(self):
        self.engine.start()
        print("Car started")

engine = Engine()
car = Car(engine)
car.start()
```

### Example 2
```python
class Car:
    def __init__(self, engine):
        self.engine = engine


class GasEngine:
    def __init__(self, horse_power):
        self.hp = horse_power

    def start(self):
        print('Starting {}hp gas engine'.format(self.hp))


class DieselEngine:
    def __init__(self, horse_power):
        self.hp = horse_power

    def start(self):
        print('Starting {}hp diesel engine'.format(self.hp))


my_car = Car(GasEngine(4))
my_car.engine.start()
my_car.engine = DieselEngine(2)
my_car.engine.start()
```

The “Car” class is loosely coupled with the “engine” component. It’s a composite object.

The main advantages are:

    - whenever a change is applied to the engine object, it does not influence the “Car” class object structure;
    - you can decide what your car should be equipped with.

Our “Car” could be equipped with two different kinds of engine – a gas one or a diesel one. The developer's responsibility is to provide methods for both engine classes, named in the same way (here is thestart() method) to make it work in a polymorphic manner.

Run the code to confirm your expectations.

- To favor composition over inheritance is a design principle that gives the design higher flexibility, as you can choose which domain-specific objects should be incorporated into your ultimate object. It's like arming your base machine with tooling, dedicated to running a specific task, but not building a wide hierarchy structure of classes covering all possible hardware combinations. 
- In fact, with the composition approach you can more easily respond to the requirement changes regarding classes, as it does not require deep dependency investigations which you would spot while implementing code with the inheritance approach.
- On the other hand, there is a clear drawback: composition transfers additional responsibilities to the developer. The developer should assure that all component classes that are used to build the composite should implement the methods named in the same manner to provide a common interface.
- In the case of inheritance, if the developer forgets to implement a specific method, the inherited method with the same name will be called. Additionally, in the case of inheritance, the developer has to re-implement only the specific methods, not all of them, to gain a common interface.


## Inheritance

Inheritance is a mechanism where a new class inherits attributes and methods from an existing class. It promotes code reuse and establishes a relationship between the parent and child classes.

- Inheritance extends a class's capabilities by adding new components and modifying existing ones; in other words, the complete recipe is contained inside the class itself and all its ancestors; the object takes all the class's belongings and makes use of them;

### Example

```python
class Vehicle:
    def start(self):
        print("Vehicle started")

class Car(Vehicle):
    def start(self):
        super().start()
        print("Car started")

car = Car()
car.start()
```

## When to Use

- **Composition**: Use when you want to build complex objects from simpler ones and promote flexibility.
- **Inheritance**: Use when there is a clear hierarchical relationship and you want to reuse code from the parent class.
- Inheritance and composition are not mutually exclusive. Real-life problems are hardly every pure “is a” or “has a” cases;
- treat both inheritance and composition as supplementary means for solving problems;
- there is nothing wrong with composing objects of ... classes that were built using inheritance. The next example code should shed some light on this case.
- You should always examine the problem your code is about to solve before you start coding. If the problem can be modeled using an “is a” relation, then the inheritance approach should be implemented.
- Otherwise, if the problem can be modeled using a “has a” relation, then the choice is clear – composition is the solution. 

```python
class Base_Computer:
    def __init__(self, serial_number):
        self.serial_number = serial_number


class Personal_Computer(Base_Computer):
    def __init__(self, sn, connection):
        super().__init__(sn)
        self.connection = connection
        print('The computer costs $1000')


class Connection:
    def __init__(self, speed):
        self.speed = speed

    def download(self):
        print('Downloading at {}'.format(self.speed))


class DialUp(Connection):
    def __init__(self):
        super().__init__('9600bit/s')

    def download(self):
        print('Dialling the access number ... '.ljust(40), end='')
        super().download()


class ADSL(Connection):
    def __init__(self):
        super().__init__('2Mbit/s')

    def download(self):
        print('Waking up modem  ... '.ljust(40), end='')
        super().download()


class Ethernet(Connection):
    def __init__(self):
        super().__init__('10Mbit/s')

    def download(self):
        print('Constantly connected... '.ljust(40), end='')
        super().download()

# I started my IT adventure with an old-school dial up connection
my_computer = Personal_Computer('1995', DialUp())
my_computer.connection.download()

# then in the year 1999 I got ADSL
my_computer.connection = ADSL()
my_computer.connection.download()

# finally I upgraded to Ethernet
my_computer.connection = Ethernet()
my_computer.connection.download()

#output
#The computer costs $1000
#Dialling the access number ...          Downloading at 9600bit/s
#Waking up modem  ...                    Downloading at 2Mbit/s
#Constantly connected...                 Downloading at 10Mbit/s


```

- There is a “Base_Computer” class that represents a generic computer. A generic computer has only a serial number;
- there is a “Personal_Computer” class that is built upon the “Base_Computer” class and represents a computer that is able to connect to the internet;
- there is a generic “Connection” class that holds information about the connection speed and handles the download() method. This class is independent of any computer class;
- there are the “Connection” subclasses, more specialized than the “Connection” class:
  - “Dialup”
  - “ADSL”
  - “Ethernet”

* When we start with our personal computer, we set the serial number to 1995 and equip it with a dialup connection. This an example of composition.

- It is possible to download some data using a slow dialup connection;
- later, we equip our personal computer with a more advanced connection device. There is no need to recreate the computer object – we just arm it with a new component;
- the last steps are about arming our old computer with a fast connection and downloading some data.
