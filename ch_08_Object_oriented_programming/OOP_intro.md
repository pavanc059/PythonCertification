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
```
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
```
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

```
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
```
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
```
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
 ```
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
```
class Classy:
    def method(self):
        print("method")

obj = Classy()
obj.method()

```
`Note the way we've created the object - we've treated the class name like a function, returning a newly instantiated object of the class.`
- The `self` parameter is used to obtain access to the object's instance and class variables.
```
class Classy:
    varia = 2
    def method(self):
        print(self.varia, self.var)

obj = Classy()
obj.var = 3
obj.method()
```
- The `self` parameter is also used to invoke other object/class methods from inside the class.
```
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
```
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

```
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
```
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