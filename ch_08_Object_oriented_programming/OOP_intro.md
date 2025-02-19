# Introduction to Object-Oriented Programming

This very important approach is present in most computer applications because it allows programmers to model entities representing real-life objects. Moreover, OOP allows programmers to model interactions between objects in order to solve real-life problems in an efficient, comfortable, extendable, and well-structured manner.

- > class — an idea, blueprint, or recipe for an instance;
- > instance — an instantiation of the class; very often used interchangeably with the term 'object';
- > object — Python's representation of data and methods; objects could be aggregates of instances;
- > attribute — any object or class trait; could be a variable or method;
- > method — a function built into a class that is executed on behalf of the class or object; some say that it’s a 'callable attribute';
- > type — refers to the class that was used to instantiate the object.



## Class
- A class is like a recipe which can be used when you want to create a useful object (this is where the name of the approach comes from). You may produce as many objects as you  need to solve your problem.
- Every object has a set of traits (they are called properties or attributes - we'll use both words synonymously) and is able to perform a set of activities (which are called methods).

### What is an object?
- A class (among other definitions) is a set of objects. An object is a being belonging to a class.

- An object is an incarnation of the requirements, traits, and qualities assigned to a specific class. This may sound simple, but note the following important circumstances. Classes form a hierarchy. This may mean that an object belonging to a specific class belongs to all the superclasses at the same time. It may also mean that any object belonging to a superclass may not belong to any of its subclasses.

#### What does an object have?
 The object programming convention assumes that every existing object may be equipped with three groups of attributes:
 - An object has a name that uniquely identifies it within its home namespace (although there may be some anonymous objects, too)
 - An object has a set of individual properties which make it original, unique or outstanding (although it's possible that some objects may have no properties at all)
 - An object has a set of abilities to perform specific activities, able to change the object itself, or some of the other objects.

#### What is an attribute
An attribute is a capacious term that can refer to two major kinds of class traits:
- Variables, containing information about the class itself or a class instance; classes and class instances can own many variables;
- Methods, formulated as Python functions; they represent a behavior that could be applied to the object.
- Each Python object has its own individual set of attributes. We can extend that set by adding new attributes to existing objects, change (reassign) them or control access to those attributes.
- Class attributes are most often addressed with 'dot' notation, i.e., `<class>`dot`<attribute>`. The other way to access attributes (variables) it to use the getattr() and setattr() functions.

#### Creating a class :
 - Object programming is the art of defining and expanding classes. A class is a model of a very specific part of reality, reflecting properties and activities found in the real world.
 - There's no obstacle to defining new, more precise subclasses. They'll inherit everything from their superclass, so the work that went into its creation isn't wasted.
 - The new class may add new properties and new activities, and therefore may be more useful in specific applications. Obviously, it may be used as a superclass for any number of newly created subclasses.
 - The class you define has nothing to do with the object: the existence of a class does not mean that any of the compatible objects will automatically be created. The class itself isn't able to create an object - you have to create it yourself, and Python allows you to do this.
 - It's time to define the simplest class and to create an object. Take a look at the example below:
    ```
    class TheSimplestClass:
        pass
    ```

#### Creating an Object :
 - The newly defined class becomes a tool that is able to create new objects. The tool has to be used explicitly, on demand.
 - To create a object, you need to assign a variable to store the newly created object of that class, and create an object at the same time.
 ```
 myFirstObject = TheSimplestClass()
 ```
 - The newly created object is equipped with everything the class brings; as this class is completely empty, the object is empty, too.
 - The act of creating an object of the selected class is also called an instantiation (as the object becomes an instance of the class).

### OOP Properties :
#### Instance variables :
- In general, a class can be equipped with two different kinds of data to form a class's properties. You already saw one of them when we were looking at stacks.

- This kind of class property exists when and only when it is explicitly created and added to an object. As you already know, this can be done during the object's initialization, performed by the constructor.

- Moreover, it can be done in any moment of the object's life. Furthermore, any existing property can be removed at any time.

```Such an approach has some important consequences:```

    - different objects of the same class may possess different sets of properties;
    - there must be a way to safely check if a specific object owns the property you want to utilize (unless you want to provoke an exception - it's always worth considering)
    - each object carries its own set of properties - they don't interfere with one another in any way.
- Property to an object can be set on fly
Example :
```python
class ExampleClass:
    def __init__(self, val = 1):
        self.first = val

    def setSecond(self, val):
        self.second = val

exampleObject3 = ExampleClass(4)
exampleObject3.third = 5
print(exampleObject3.__dict__)

output : {'first': 4, 'third': 5}

```
```python
class ExampleClass:
    def __init__(self, val = 1):
        self.__first = val

    def setSecond(self, val = 2):
        self.__second = val


exampleObject1 = ExampleClass()
exampleObject2 = ExampleClass(2)

exampleObject2.setSecond(3)

exampleObject3 = ExampleClass(4)
exampleObject3.__third = 5


print(exampleObject1.__dict__)
print(exampleObject2.__dict__)
print(exampleObject3.__dict__)

output:
{'_ExampleClass__first': 1}
{'_ExampleClass__first': 2, '_ExampleClass__second': 3}
{'_ExampleClass__first': 4, '__third': 5}
```
- It's nearly the same as the previous one. The only difference is in the property names. We've added two underscores (__) in front of them. As you know, such an addition makes the instance variable private.It becomes inaccessible from the outer world.
- When Python sees that you want to add an instance variable to an object   and you're going to do it inside any of the object's methods, it mangles the operation in the following way:
    - it puts a class name before your name;
    - it puts an additional underscore at the beginning.
- This is why the __first becomes _ExampleClass__first. The name is now fully accessible from outside the class.
``` 
print(exampleObject1._ExampleClass__first) 

```
- Any instance variable added outside the class will act like ordinary property "exampleObject3.__third = 5"
To print actual values 
```
print(exampleObject1._ExampleClass__first)
print(exampleObject2._ExampleClass__second)
print(exampleObject3.__third)
```
#### Class Variables :
- A class variable is a property which exists in just one copy and is stored outside any object.
 
 ```Note: no instance variable exists if there is no object in the class; a class variable exists in one copy even if there are no objects in the class.```

```python
class ExampleClass:
    counter = 0
    def __init__(self, val = 1):
        self.__first = val
        ExampleClass.counter += 1

exampleObject1 = ExampleClass()
exampleObject2 = ExampleClass(2)
exampleObject3 = ExampleClass(4)

print(exampleObject1.__dict__, exampleObject1.counter)
print(exampleObject2.__dict__, exampleObject2.counter)
print(exampleObject3.__dict__, exampleObject3.counter)

output:
{'_ExampleClass__first': 1} 3
{'_ExampleClass__first': 2} 3
{'_ExampleClass__first': 4} 3
```
- there is an assignment in the first list of the class definition - it sets the variable named counter to 0; initializing the variable inside the class but outside any of its methods makes the variable a class variable;
- accessing such a variable looks the same as accessing any instance attribute - you can see it in the constructor body; as you can see, the constructor increments the variable by one; in effect, the variable counts all the created objects.
```Two important conclusions come from the example:```
1) class variables aren't shown in an object's __dict__ (this is natural as class variables aren't parts of an object) but you can always try to look into the variable of the same name, but at the class level.
2) a class variable always presents the same value in all class instances (objects)

- Making class variable as private will have same effect as making instance variable as private
```
class ExampleClass:
    __counter = 0
    def __init__(self, val = 1):
        self.__first = val
        ExampleClass.__counter += 1

exampleObject1 = ExampleClass()
exampleObject2 = ExampleClass(2)
exampleObject3 = ExampleClass(4)

print(exampleObject1.__dict__, exampleObject1._ExampleClass__counter)
print(exampleObject2.__dict__, exampleObject2._ExampleClass__counter)
print(exampleObject3.__dict__, exampleObject3._ExampleClass__counter)

Output : 
{'_ExampleClass__first': 1} 3
{'_ExampleClass__first': 2} 3
{'_ExampleClass__first': 4} 3
```

- Class variables exist even when no class instance (object) had been created.
```python
class ExampleClass:
    varia = 1
    def __init__(self, val):
        ExampleClass.varia = val

print(ExampleClass.__dict__)
exampleObject = ExampleClass(2)

print(ExampleClass.__dict__)
print(exampleObject.__dict__)

output :
{'__module__': '__main__', 'varia': 1, '__init__': <function ExampleClass.__init__ at 0x7fb4c76094d0>, '__dict__': <attribute '__dict__' of 'ExampleClass' objects>, '__weakref__': <attribute '__weakref__' of 'ExampleClass' objects>, '__doc__': None}

{'__module__': '__main__', 'varia': 2, '__init__': <function ExampleClass.__init__ at 0x7fb4c76094d0>, '__dict__': <attribute '__dict__' of 'ExampleClass' objects>, '__weakref__': <attribute '__weakref__' of 'ExampleClass' objects>, '__doc__': None}

{}

- changing the assignment to self.varia = val 
class ExampleClass:
    varia = 1
    def __init__(self, val):
        self.varia = val

print(ExampleClass.__dict__)

exampleObject1 = ExampleClass(3)
print(exampleObject1.__dict__)
print(exampleObject1.varia) # changing assignment to self.varia creates an instance variable 
print(ExampleClass.varia) # class variable of same name is unchanged

Output : 
{'__module__': '__main__', 'varia': 1, '__init__': <function ExampleClass.__init__ at 0x7fb849ff34d0>, '__dict__': <attribute '__dict__' of 'ExampleClass' objects>, '__weakref__': <attribute '__weakref__' of 'ExampleClass' objects>, '__doc__': None}

{'varia': 3}

3

1


- changing the assignment to varia = val
class ExampleClass:
    varia = 1
    def __init__(self, val):
        varia = val

print(ExampleClass.__dict__)

exampleObject1 = ExampleClass(3)
print(exampleObject1.__dict__) # here there's no instance properties
print(exampleObject1.varia) # varia = val creates a method local variable within the method instead of modifying the instance variable and this local variable discards after __init__ method and only class variable named ```varia``` will be accessed
print(ExampleClass.varia) # Here we're accessing class variable which is unchanged  


Output :
{'__module__': '__main__', 'varia': 1, '__init__': <function ExampleClass.__init__ at 0x7f3815c8e4d0>, '__dict__': <attribute '__dict__' of 'ExampleClass' objects>, '__weakref__': <attribute '__weakref__' of 'ExampleClass' objects>, '__doc__': None}

{}

1

1

```
- we define one class named ExampleClass;
- the class defines one class variable named ```varia```.
- the class constructor sets the variable with the parameter's value;
- naming the variable is the most important aspect of the example because:
    - changing the assignment to self.varia = val would create an instance variable of the same name as the class's one;
    - changing the assignment to varia = val would operate on a method's local variable; (we strongly encourage you to test both of the above cases - this will make it easier for you to remember the difference)
- the first line of the off-class code prints the value of the ExampleClass.varia attribute; note - we use the value before the very first object of the class is instantiated.

#### Checking an attribute's existence :
    Python's attitude to object instantiation raises one important issue - in contrast to other programming languages, you may not expect that all objects of the same class have the same sets of properties.
```python
class ExampleClass:
    def __init__(self, val):
        if val % 2 != 0:
            self.a = 1
        else:
            self.b = 1

exampleObject = ExampleClass(1)

print(exampleObject.a)
print(exampleObject.b)

Output :
1
Traceback (most recent call last):
  File ".main.py", line 11, in 
    print(exampleObject.b)
AttributeError: 'ExampleClass' object has no attribute 'b'

```
- The object created by the constructor can have only one of two possible attributes: a or b.
- As you can see, accessing a non-existing object (class) attribute causes an AttributeError exception.
- The try-except instruction gives you the chance to avoid issues with non-existent properties.
- Python provides a function which is able to safely check if any object/class contains a specified property. The function is named hasattr, and expects two arguments to be passed to it:
    1) the class or the object being checked;
    2) the name of the property whose existence has to be reported (note: it has to be a string containing the attribute name, not the name alone)
    The function returns True or False.
```
print(exampleObject.a)

try:
    print(exampleObject.b)
except AttributeError:
    pass
```
- The hasattr() function can operate on classes, too. You can use it to find out if a class variable is available.

Ecample :
 ```python
 class ExampleClass:
    a = 1
    def __init__(self):
        self.b = 2

exampleObject = ExampleClass()

print(hasattr(exampleObject, 'b'))
print(hasattr(exampleObject, 'a'))
print(hasattr(ExampleClass, 'b'))
print(hasattr(ExampleClass, 'a'))

Output :
True
True
False
True
```

#### Methods
 A method is a function embedded inside a class.
- There is one fundamental requirement a method is obliged to have at least one parameter (there are no such thing as parameterless methods a method may be invoked without an argument, but not declared without parameters).
- The first (or only) parameter is usually named ```self``` we need to use same name as first parameter.
- The name self suggests the parameter's purpose - it identifies the object for which the method is invoked.
```python
class Classy:
    def method(self):
        print("method")

obj = Classy()
obj.method()

```
`Note the way we've created the object - we've treated the class name like a function, returning a newly instantiated object of the class.`
- The `self` parameter is used to obtain access to the object's instance and class variables.
```python
class Classy:
    varia = 2
    def method(self):
        print(self.varia, self.var)

obj = Classy()
obj.var = 3
obj.method()
```
- The `self` parameter is also used to invoke other object/class methods from inside the class.
```python
class Classy:
    def other(self):
        print("other")

    def method(self):
        print("method")
        self.other()

obj = Classy()
obj.method()
```
- If you name a method like this: ```__init__```, it won't be a regular method - it will be a constructor.
- If a class has a constructor, it is invoked automatically and implicitly when the object of the class is instantiated.

_____________________________________________________________________________________________________________________________________________________
##### Constructor 
- is obliged to have the self parameter (it's set automatically, as usual);
- may (but doesn't need to) have more parameters than just self; if this happens, the way in which the class name is used to create the object must reflect the __init__ definition;
- can be used to set up the object, i.e., properly initialize its internal state, create instance variables, instantiate any other objects if their existence is needed, etc.
- cannot return a value, as it is designed to return a newly created object and nothing else;
- cannot be invoked directly either from the object or from inside the class (you can invoke a constructor from any of the object's superclasses, but we'll discuss this issue later.)
______________________________________________________________________________________________________________________________________________________
- As `__init__` is a method, and a method is a function, you can do the same tricks with constructors/methods as you do with ordinary functions.
- Everything about property name mangling applies to method names, too - a method whose name starts with `__` is (partially) hidden.
```python
class Classy:
    def visible(self):
        print("visible")
    
    def __hidden(self):
        print("hidden")

obj = Classy()
obj.visible()

try:
    obj.__hidden()
except:
    print("failed")

obj._Classy__hidden()

output:
visible
failed
hidden
```
#### The inner life of classes and objects
- Each Python class and each Python object is pre-equipped with a set of useful attributes which can be used to examine its capabilities.
- These attributes can we found using `__dict__` property of object or class

```python
class Classy:
    varia = 1
    def __init__(self):
        self.var = 2

    def method(self):
        pass

    def __hidden(self):
        pass

obj = Classy()

print(obj.__dict__)
print(Classy.__dict__)

output:
{'var': 2}

{'__module__': '__main__', 'varia': 1, '__init__': <function Classy.__init__ at 0x7f1107f53320>, 'method': <function Classy.method at 0x7f1107f53ef0>, '_Classy__hidden': <function Classy.__hidden at 0x7f1107f53f80>, '__dict__': <attribute '__dict__' of 'Classy' objects>, '__weakref__': <attribute '__weakref__' of 'Classy' objects>, '__doc__': None}
```

- `__dict__` is a dictionary. Another built-in property worth mentioning is `__name__`, which is a string.
- The property contains the name of the class. `Note: the __name__ attribute is absent from the object - it exists only inside classes.`
- If you want to find the class of a particular object, you can use a function named type(), which is able (among other things) to find a class which has been used to instantiate any object.

```
class Classy:
    pass

print(Classy.__name__)
obj = Classy()
print(type(obj).__name__)

output: 
Classy
Classy

class Classy:
    pass

print(Classy.__module__)
obj = Classy()
print(obj.__module__)

output :
__main__
__main__


```
- `__module__` is a string, too - it stores the name of the module which contains the definition of the class.
- `__main__` is actually not a module, but the file currently being run.
- `__bases__` is a tuple. The tuple contains classes (not class names) which are direct superclasses for the class  and  only classes have this attribute objects don't.
- A class without explicit superclasses points to object (a predefined Python class) as its direct ancestor.
```python
class SuperOne:
    pass

class SuperTwo:
    pass

class Sub(SuperOne, SuperTwo):
    pass


def printBases(cls):
    print('( ', end='')

    for x in cls.__bases__:
        print(x.__name__, end=' ')
    print(')')


printBases(SuperOne)
printBases(SuperTwo)
printBases(Sub)

output :
( object )
( object )
( SuperOne SuperTwo )
```
#### Reflection and introspection
This will allow the Python programmer to perform two important activities specific to many objective languages. They are:
- Introspection, which is the ability of a program to examine the type or properties of an object at runtime;
- Reflection, which goes a step further, and is the ability of a program to manipulate the values, properties and/or functions of an object at runtime.

```python linenums="1"
class MyClass:
    pass

obj = MyClass()
obj.a = 1
obj.b = 2
obj.i = 3
obj.ireal = 3.5
obj.integer = 4
obj.z = 5

def incIntsI(obj):
    for name in obj.__dict__.keys():
        if name.startswith('i'):
            val = getattr(obj, name)
            if isinstance(val, int):
                setattr(obj, name, val + 1)

print(obj.__dict__)
incIntsI(obj)
print(obj.__dict__)

Output : 
{'a': 1, 'integer': 4, 'b': 2, 'i': 3, 'z': 5, 'ireal': 3.5}
{'a': 1, 'integer': 5, 'b': 2, 'i': 4, 'z': 5, 'ireal': 3.5}
```
The function named incIntsI() gets an object of any class, scans its contents in order to find all integer attributes with names starting with i, and increments them by one.
- line 1: define a very simple class
- lines 3 through 10: ... and fill it with some attributes;
- line 12: this is our function!
- line 13: scan the `__dict__` attribute, looking for all attribute names;
- line 14: if a name starts with i...
- line 15: ... use the getattr() function to get its current value; note: getattr() takes two arguments: an object, and its property name (as a string), and returns the current attribute's value;
- line 16: check if the value is of type integer, and use the function isinstance() for this purpose (we'll discuss this later);
- line 17: if the check goes well, increment the property's value by making use of the setattr() function; the function takes three arguments: an object, the property name (as a string), and the property's new value.

#### Inheritance :
Start  with default functions example 
```python
class Star:
    def __init__(self, name, galaxy):
        self.name = name
        self.galaxy = galaxy

sun = Star("Sun", "Milky Way")
print(sun)

output:
<__main__.Star object at 0x000002437610CE60> # in my machine 

`Now you can overried the default object function by implemeting `__str__()` function`

class Star:
    def __init__(self, name, galaxy):
        self.name = name
        self.galaxy = galaxy

    def __str__(self):
        return self.name + ' in ' + self.galaxy

sun = Star("Sun", "Milky Way")
print(sun)

Output :
Sun in Milky Way
```
`Inheritance` is a common practice (in object programming) of passing attributes and methods from the superclass (defined and existing) to a newly created class, called the subclass.
- In other words, inheritance is a way of building a new class, not from scratch, but by using an already defined attributes/properties. The new class inherits (and this is the key) all the already existing equipment, but is able to add some new ones if needed.
- It's possible to build more specialized (more concrete) classes using some sets of predefined general rules and behaviors.
- The most important factor of the process is the relation between the superclass and all of its subclasses (note: if B is a subclass of A and C is a subclass of B, this also means than C is a subclass of A, as the relationship is fully transitive).

```python
#A very simple example of two-level inheritance is presented here:
class Vehicle:
    pass

class LandVehicle(Vehicle):
    pass

class TrackedVehicle(LandVehicle):
    pass

for cls1 in [Vehicle, LandVehicle, TrackedVehicle]:
    for cls2 in [Vehicle, LandVehicle, TrackedVehicle]:
        print(issubclass(cls1, cls2), end="\t")
    print()

↓ is a subclass of → 	Vehicle 	LandVehicle 	TrackedVehicle
Vehicle 	              True 	        False 	        False
LandVehicle 	          True 	        True 	        False
TrackedVehicle 	          True 	        True 	        True

myVehicle = Vehicle()
myLandVehicle = LandVehicle()
myTrackedVehicle = TrackedVehicle()

for obj in [myVehicle, myLandVehicle, myTrackedVehicle]:
    for cls in [Vehicle, LandVehicle, TrackedVehicle]:
        print(isinstance(obj, cls), end="\t")
    print()

↓ is an instance of → 	Vehicle 	LandVehicle 	TrackedVehicle
myVehicle 	              True 	        False 	        False
myLandVehicle 	          True 	        True 	        False
myTrackedVehicle 	      True 	        True 	        True


```
- The Vehicle class is the superclass for both the LandVehicle and TrackedVehicle classes;
- The LandVehicle class is a subclass of Vehicle and a superclass of TrackedVehicle at the same time;
- The TrackedVehicle class is a subclass of both the Vehicle and LandVehicle classes.

`issubclass()` Python offers a function which is able to identify a relationship between two classes, and although its diagnosis isn't complex, it can check if a particular class is a subclass of any other class.

`issubclass(ClassOne, ClassTwo)` The function returns True if ClassOne is a subclass of ClassTwo, and False otherwise.

`isinstance()` This function determines if an object is instance of a specific class or instance of one of its subclass
`isinstance(objectName, ClassName)` function returns True if objectName is instance of class or one of its subclass

`"is" operator` The is operator checks whether two variables (objectOne and objectTwo here) refer to the same object.
- variables don't store the objects themselves, but only the handles pointing to the internal Python memory.
- Assigning a value of an object variable to another variable doesn't copy the object, but only its handle. 

```python
class SampleClass:
    def __init__(self, val):
        self.val = val

ob1 = SampleClass(0)
ob2 = SampleClass(2)
ob3 = ob1
ob3.val += 1

print(ob1 is ob2)
print(ob2 is ob3)
print(ob3 is ob1)
print(ob1.val, ob2.val, ob3.val)

str1 = "Mary had a little "
str2 = "Mary had a little lamb"
str1 += "lamb"

print(str1 == str2, str1 is str2)
 
Output:
False
False
True
1 2 1
True False
```
- There is a very simple class equipped with a simple constructor, creating just one property. The class is used to instantiate two objects. The former is then assigned to another variable, and its val property is incremented by one.
- Afterward, the is operator is applied three times to check all possible pairs of objects, and all val property values are also printed.
- The last part of the code carries out another experiment. After three assignments, both strings contain the same texts, but these texts are stored in different objects.

```python
class Super:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "My name is " + self.name + "."

class Sub(Super):
    def __init__(self, name):
        Super.__init__(self, name)


obj = Sub("Andy")

print(obj)

Output :
My name is Andy.
```
- There is a class named Super, which defines its own constructor used to assign the object's property, named name.
- The class defines the __str__() method, too, which makes the class able to present its identity in clear text form.
- The class is next used as a base to create a subclass named Sub. The Sub class defines its own constructor, which invokes the one from the superclass. Note how we've done it: Super.__init__(self, name).
- We've explicitly named the superclass, and pointed to the method to invoke __init__(), providing all needed arguments.
- We've instantiated one object of class Sub and printed it.

`super()` function, which accesses the superclass without needing to know its name and which used invoke superclass and it creates a context in which you don't have to pass the self argument to the method being invoked - this is why it's possible to activate the superclass constructor using only one argument.

`Note: you can use this mechanism not only to invoke the superclass constructor, but also to get access to any of the resources available inside the superclass.`

```python
class Super:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "My name is " + self.name + "."

class Sub(Super):
    def __init__(self, name):
        super().__init__(name)


obj = Sub("Andy")

print(obj)

Output:
My name is Andy.
```

```python
class Level1:
    varia1 = 100
    def __init__(self):
        self.var1 = 101

    def fun1(self):
        return 102


class Level2(Level1):
    varia2 = 200
    def __init__(self):
        super().__init__()
        self.var2 = 201
    
    def fun2(self):
        return 202


class Level3(Level2):
    varia3 = 300
    def __init__(self):
        super().__init__()
        self.var3 = 301

    def fun3(self):
        return 302


obj = Level3()

print(obj.varia1, obj.var1, obj.fun1())
print(obj.varia2, obj.var2, obj.fun2())
print(obj.varia3, obj.var3, obj.fun3())

Output : 
100 101 102
200 201 202
300 301 302

```
- When you try to access any object's entity, Python will try to (in this order):

    - find it inside the object itself;
    - find it in all classes involved in the object's inheritance line from bottom to top;

- If both of the above fail, an exception (AttributeError) is raised.

- The first condition may need some additional attention. As you know, all objects deriving from a particular class may have different sets of attributes, and some of the attributes may be added to the object a long time after the object's creation.

- All the comments we've made so far are related to single inheritance, when a subclass has exactly one superclass. This is the most common situation (and the recommended one, too).

- Python, however, offers much more here. In the next lessons we're going to show you some examples of multiple inheritance.

##### Multiple inheritance :
Multiple inheritance occurs when a class has more than one superclass.

- Syntactically, such inheritance is presented as a comma-separated list of superclasses put inside parentheses after the new class name - just like here:
```python
class SuperA:
    varA = 10
    def funA(self):
        return 11

class SuperB:
    varB = 20
    def funB(self):
        return 21

class Sub(SuperA, SuperB):
    pass

obj = Sub()

print(obj.varA, obj.funA())
print(obj.varB, obj.funB())
```

- The Sub class has two superclasses: SuperA and SuperB. This means that the Sub class inherits all the goods offered by both SuperA and SuperB.

```python
class Level1:
    var = 100
    def fun(self):
        return 101

class Level2(Level1):
    var = 200
    def fun(self):
        return 201

class Level3(Level2):
    pass

obj = Level3()

print(obj.var, obj.fun())

Output :
200 201
```
- Both, Level1 and Level2 classes define a method named fun() and a property named var. Does this mean that the Level3 class object will be able to access two copies of each entity? Not at all.
- The entity defined later (in the inheritance sense) overrides the same entity defined earlier.
- The var class variable and fun() method from the Level2 class override the entities of the same names derived from the Level1 class.
- This feature can be intentionally used to modify default (or previously defined) class behaviors when any of its classes needs to act in a different way to its ancestor.
- Python looks for an entity from bottom to top, and is fully satisfied with the first entity of the desired name.

```python
class Left:
    var = "L"
    varLeft = "LL"
    def fun(self):
        return "Left"


class Right:
    var = "R"
    varRight = "RR"
    def fun(self):
        return "Right"

class Sub(Left, Right):
    pass


obj = Sub()

print(obj.var, obj.varLeft, obj.varRight, obj.fun())

Output:
L LL RR Left

class Sub(Right, Left):
    pass


obj = Sub()

print(obj.var, obj.varLeft, obj.varRight, obj.fun())

Output:
R LL RR Right
```
- The Sub class inherits goods from two superclasses, Left and Right
- There is no doubt that the class variable varRight comes from the Right class, and varLeft comes from Left respectively.

This is clear. But where does var come from? Is it possible to guess it? The same problem is encountered with the fun() method - will it be invoked from Left or from Right?

We can say that Python looks for object components in the following order:

    - Inside the object itself;
    - In its superclasses, from bottom to top;
    - If there is more than one class on a particular inheritance path, Python scans them from left to right.

```python
class One:
    def doit(self):
        print("doit from One")

    def doanything(self):
        self.doit()

class Two(One):
    def doit(self):
        print("doit from Two")

one = One()
two = Two()

one.doanything()
two.doanything()

Output : 
doit from One
doit from Two
```
- There are two classes, named One and Two, while Two is derived from One. Nothing special. However, one thing looks remarkable - the doit() method.
- The doit()method is defined twice: originally inside One and subsequently inside Two. The essence of the example lies in the fact that it is invoked just once - inside One.
- The first invocation seems to be simple, and it is simple, actually - invoking doanything() from the object named one will obviously activate the first of the methods.
- The second invocation needs some attention. It's simple, too if you keep in mind how Python finds class components. The second invocation will launch doit() in the form existing inside the Two class, regardless of the fact that the invocation takes place within the One class.
- The method, redefined in any of the superclasses, thus changing the behavior of the superclass, is called virtual.

`Note: the situation in which the subclass is able to modify its superclass behavior is called polymorphism. The word comes from Greek (polys: "many, much" and morphe, "form, shape"), which means that one and the same class can take various forms depending on the redefinitions done by any of its subclasses.`

#### Polymorphism 
The situation in which the subclass is able to modify its superclass behavior is called polymorphism.

```python
import time

class Vehicle:
    def changedirection(left, on):
        pass

    def turn(left):
        changedirection(left, True)
        time.sleep(0.25)
        changedirection(left, False)

class TrackedVehicle(Vehicle):
    def controltrack(left, stop):
        pass

    def changedirection(left, on):
        controltrack(left, on)

class WheeledVehicle(Vehicle):
    def turnfrontwheels(left, on):
        pass

    def changedirection(left, on):
        turnfrontwheels(left, on)
```

- we defined a superclass named Vehicle, which uses the turn() method to implement a general scheme of turning, while the turning itself is done by a method named changedirection(); note: the former method is empty, as we are going to put all the details into the subclass (such a method is often called an abstract method, as it only demonstrates some possibility which will be instantiated later)
- we defined a subclass named TrackedVehicle (note: it's derived from the Vehicle class) which instantiated the changedirection() method by using the specific (concrete) method named controltrack()
- respectively, the subclass named WheeledVehicle does the same trick, but uses the turnfrontwheel() method to force the vehicle to turn.
- The most important advantage (omitting readability issues) is that this form of code enables you to implement a brand new turning algorithm just by modifying the turn() method, which can be done in just one place, as all the vehicles will obey it.

- Inheritance is not the only way of constructing adaptable classes. You can achieve the same goals (not always, but very often) by using a technique named composition.

Composition is the process of composing an object using other different objects. The objects used in the composition deliver a set of desired traits (properties and/or methods) so we can say that they act like blocks used to build a more complicated structure.

It can be said that:

    - inheritance extends a class's capabilities by adding new components and modifying existing ones; in other words, the complete recipe is contained inside the class itself and all its ancestors; the object takes all the class's belongings and makes use of them;
    - composition projects a class as a container able to store and use other objects (derived from other classes) where each of the objects implements a part of a desired class's behavior.

```python
import time

class Tracks:
    def changedirection(self, left, on):
        print("tracks: ", left, on)

class Wheels:
    def changedirection(self, left, on):
        print("wheels: ", left, on)

class Vehicle:
    def __init__(self, controller):
        self.controller = controller

    def turn(self, left):
        self.controller.changedirection(left, True)
        time.sleep(0.25)
        self.controller.changedirection(left, False)

wheeled = Vehicle(Wheels())
tracked = Vehicle(Tracks())

wheeled.turn(True)
tracked.turn(False)
```

- The subclasses implemented this ability by introducing specialized mechanisms. Let's do (almost) the same thing, but using composition. The class - like in the previous example - is aware of how to turn the vehicle, but the actual turn is done by a specialized object stored in a property named controller. The controller is able to control the vehicle by manipulating the relevant vehicle's parts.
- There are two classes named Tracks and Wheels - they know how to control the vehicle's direction. There is also a class named Vehicle which can use any of the available controllers (the two already defined, or any other defined in the future) - the controller itself is passed to the class during initialization.
- In this way, the vehicle's ability to turn is composed using an external object, not implemented inside the Vehicle class.

#### Single inheritance vs. multiple inheritance
As you already know, there are no obstacles to using multiple inheritance in Python. You can derive any new class from more than one previously defined classes.

- A single inheritance class is always simpler, safer, and easier to understand and maintain;
- Multiple inheritance is always risky, as you have many more opportunities to make a mistake in identifying these parts of the superclasses which will effectively influence the new class;
- Multiple inheritance may make overriding extremely tricky; moreover, using the super() function becomes ambiguous;
- Multiple inheritance violates the single responsibility principle (more details here: https://en.wikipedia.org/wiki/Single_responsibility_principle) as it makes a new class of two (or more) classes that know nothing about each other;
- We strongly suggest multiple inheritance as the last of all possible solutions - if you really need the many different functionalities offered by different classes, composition may be a better alternative.
