1) By default Python uses UTF-8 encoding to change default encoding you need to insert below comment line with encoding scheme

# -*- coding: encoding -*

  #!/usr/bin/env python3 (shebang)

# -*- coding: cp1252 -*-

2) Division in python always return float type to return int and discard any float value use "//"
   to calculate reminder use "%" ex : 5%2 = 1
3) To do power calculation use "**" ex: 2^4 --> 2**4 = 16
4) In interactive mode last printed expression is assigned to "_"
5) Python keywords : ['False', 'None', 'True', 'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield']
6) print function concatenation if you want to print string and integer using print function like print("String" + integer) this would throw and error because we're adding string with integer you need to parse one of the value to make it work as below

   - print("String" + str(integer)) or you can pass multiple parameters to print function  as print("String", integer)
7) Print function take multiple comma(',') separated values and 'sep' argument to separate between values and 'end' argument value to print at end print(value, ..., sep=' ', end='\n', file=sys.stdout, flush=False) Prints the values to a stream, or to sys.stdout by default. Optional keyword arguments:

   - > file: a file-like object (stream); defaults to the current sys.stdout.
     >
   - sep: string inserted between values, default a space.
   - end: string appended after the last value, default a newline.
   - flush: whether to forcibly flush the stream.
8) In python 2 == 2. (True)
9) Operator priority table

   | Priority | Operator               |             |
   | -------- | ---------------------- | ----------- |
   | 1        | +, -, ~                | unary       |
   | 2        | **                     |             |
   | 3        | *, /, //, %            |             |
   | 4        | +, -                   | binary      |
   | 5        | <<, >>                 |             |
   | 6        | <, <=, >, >=           |             |
   | 7        | ==, !=                 |             |
   | 8        | &                      |             |
   | 9        |                        |             |
   | 10       | =, +=, -=, *=, /=, %=, |             |
   |          | &=, ^=,                | =, >>=, <<= |
10) Variable assignment in python can also be done as following ways

    1) x = y = z = 5
    2) x, y, z = 5, 10, 20
11) while loop in python can have else condition which executes when you while condition body don't execute
    [syntax] : while condition:
    #while_body
    else:
    #else_condition body
12) else in for loop executes at the end of for execution
    [syntax] : for variable in range(value):
    #for_body
    else:
    #else block the executes at end of for loop
13) logical operators and bit wise operators in python. logical operators operate on final value of the expression but bit wise operators work on each bit as example below
    [Example] : i = 15; j = 22
    print(i and j) : 22
    print(i & j)   : 6
    print(j and i) : 15
    print(j & i)   : 6
14) list in python can store list of value of different types as shown below
    numbers = [10, [2,4,6], 7, 2.0, 'test']
15) swapping elements in python is simpler than swapping elements in java without creating third variable
    variable1, variable2 = variable2, variable1
16) when you copy a variable to another variable it copies the content of the variable(scalar variable) but with list when you copy one list to another it copies memory address of the list
    modifying one list can effect other list. TO actually copy list python has a syntax called slice
    [syntax] my_list[start:end] : Note end value should be last element index -1  that you wish to copy

    - start is the index of the first element included in the slice;
    - end is the index of the first element not included in the slice.
      [example] list1 = [1,2] \n list2 = [:]
17) list comprehension a special syntax used by python to fill large list
    [examples] : list = [value for i in range(8)] - this fills list with value from 0 to 7 indexes
    list2 = [x ** 2 for x in range(10)] - this used x value from for loop and substitute in calculation which results (0, 1, 4, 9,16,25, 36, 49, 64, 81)list3 = [2 ** i for i in range(8)] - (1, 2, 4, 8, 16, 32, 64, 128)
    list4 = [x for x in list2 if x % 2 != 0 ] - you can also include if condition before filling the list in python this list will contain all odd numbers
18) Python built-in functions :https://docs.python.org/3/library/functions.html

    |              |             | Built-in Functions |              |                |
    | ------------ | ----------- | ------------------ | ------------ | -------------- |
    | abs()        | delattr()   | hash()             | memoryview() | set()          |
    | all()        | dict()      | help()             | min()        | setattr()      |
    | any()        | dir()       | hex()              | next()       | slice()        |
    | ascii()      | divmod()    | id()               | object()     | sorted()       |
    | bin()        | enumerate() | input()            | oct()        | staticmethod() |
    | bool()       | eval()      | int()              | open()       | str()          |
    | breakpoint() | exec()      | isinstance()       | ord()        | sum()          |
    | bytearray()  | filter()    | issubclass()       | pow()        | super()        |
19) Python offers another convention for passing arguments, where the meaning of the argument is dictated by its name, not by its position - it's called keyword argument passing
20) Passing arguments to a function rule You can mix positional and keyword arguments fashions if you want - there is only one unbreakable rule: you have to put positional arguments before keyword arguments.
21) None keyword used for assign it to a variable (or return it as a function's result) or when you compare it with a variable to diagnose its internal state.
22) int() function converts string to integer/number we can pass second argument to convert given string formatted number to binary (2), hexa (16) or Octa (10) => Ex int("10", 2) = 2, int("A", 16) = 10
23) The `range()` function generates a sequence of numbers. It accepts integers and returns range objects. The syntax of `range()` looks as follows: `range(start, stop, step)`

    * `start` is an optional parameter specifying the starting number of the sequence (0 by default)
    * `stop` is an optional parameter specifying the end of the sequence generated (it is not included),
    * and `step` is an optional parameter specifying the difference between the numbers in the sequence (1 by default.)

    ```
    for i in range(6, 1, -2):
        print(i, end=" ")  # Outputs: 6, 4, 2

    ```
24) Bitwise operators are used to compare single bits of data **important** remark: the arguments of these operators must be integers; we must not use floats here.
25) Formatting string 
    * `r` - print as raw string (ex: print(r'test\ttest') will print test\ttest if you 'r' not specified it will print as test test)
    * `f` - format the string to substitute any code variable into to print statement (ex: print(f'Print aby variable value {variable}'))
    * `b` - Represents a sequence of bytes rather than a string. Useful for binary data manipulation. 

    ```
    sample bitwise Operations
        & does a bitwise and, e.g., x & y = 0, which is 0000 0000 in binary,
        | does a bitwise or, e.g., x | y = 31, which is 0001 1111 in binary,
        ˜ does a bitwise not, e.g., ˜ x = 240*, which is 1111 0000 in binary,
        ^ does a bitwise xor, e.g., x ^ y = 31, which is 0001 1111 in binary,
        >> does a bitwise right shift, e.g., y >> 1 = 8, which is 0000 1000 in binary,
        << does a bitwise left shift, e.g., y << 3 = , which is 1000 0000 in binary,

    ```

25. If you want to check the list's current length, you can use a function named `len()` (its name comes from  *length* )
26. Python swapping without third variable

    ```
    Other language like java 
    variable_1 = 1
    variable_2 = 2

    auxiliary = variable_1
    variable_1 = variable_2
    variable_2 = auxiliary

    In Python :
    variable_1 = 1
    variable_2 = 2

    variable_1, variable_2 = variable_2, variable_1

    swapping in list :
    my_list = [10, 1, 8, 3, 5]

    my_list[0], my_list[4] = my_list[4], my_list[0]
    my_list[1], my_list[3] = my_list[3], my_list[1]

    print(my_list)
    output : [5, 3, 8, 1, 10]

    Using list :
    my_list = [10, 1, 8, 3, 5]
    length = len(my_list)

    for i in range(length // 2):
        my_list[i], my_list[length - i - 1] = my_list[length - i - 1], my_list[i]
    ```

### Modules that are useful :

**timeit** : Tool for measuring execution time of small code snippets.

<details>
  <summary>Example</summary>
    ```python
        python -c "print('test')"
        output: test
        python -m timeit -h 
        python -m timeit -n 10
        output : 10 loops, best of 5: 10 nsec per loop
        python -m timeit -t
        output : 50000000 loops, best of 5: 8.58 nsec per loop
    ```
</details>


26) .pyc comes from the words Python and compiled. File with extension .pyc is a compiled version of a module stored in pycache folder. When Python imports a module for the first time, it translates its contents into a somewhat compiled shape. The file doesn't contain machine code - it's internal Python semi-compiled code, ready to be executed by Python's interpreter. As such a file doesn't require lots of the checks needed for a pure source file, the execution starts faster, and runs faster, too.

27) Importing module 

    there is a module named mod1;
    there is a module named mod2 which contains the import mod1 instruction;
    there is a main file containing the import mod1 and import mod2 instructions.
    \- At first glance, you may think that mod1 will be imported twice - fortunately, only the first import occurs. Python remembers the imported modules and silently omits all subsequent imports.

28) If you're trying to find a character or string in another string use find() instead of index. It's safer - it doesn't generate an error for an argument containing a non-existent substring (it returns -1 then)

29) If we're creating a method for class we should pass first parameter as ```self``` it is mandatory to get object's instance and class variables.
30) Python instance variables are created by setting them to `self` parameter i.e : `self.instanceVariable`. same applies to private class variable you need insatnce to access it.
31) You can create private instance variables by starting `__` double underscores dundor. If you want to access this instance private variable you have to access following way `instance._className__variableName`
32) To get one class attributes to another class through Inheritance we need to pass parent class name in parentheses next to class name Ex: class child(parent):
33) IF you want to make attribute absolute private you can do it by `@property`, `@.setter`, and `@.deleter` decorations if you delete  `@.setter` that will make attribute readonly
Example:
```python
class Car:
    def __init__(self, color, model, year):
        self.color = color
        self.model = model
        self.year = year
        self._voltage = 12

    @property
    def voltage(self):
        return self._voltage

    @voltage.setter
    def voltage(self, volts):
        print("Warning: this can cause problems!")
        self._voltage = volts

    @voltage.deleter
    def voltage(self):
        print("Warning: the radio will stop working!")
        del self._voltage
```
34) `__str__(self)` is the method used to override and print used defined object information like toString() method in java. when object is passed to print() function this function will be invoked.
35) `@classmethod` : class methods are used to change the state of the class it works like a multiple arguments constructors. you can have only one `__init__()` method if we define more last defined `__init__()` method will override the behavior. `@staticmethods` : are utility methods
36) To implements multiple Inheritance we need to pass to parent class with comma separated next to class name in parentheses Ex : class child(parent1, parent2):
37) Python always scans for object property or method definition in order of 1) Object itself, 2) Immediate parent bottom up and 3) In multiple Inheritance left to right.
38) `issubclass(ClassOne, ClassTwo)` The function returns True if ClassOne is a subclass of ClassTwo, and False otherwise.
39) `isinstance(objectName, ClassName)` function returns True if objectName is instance of class or one of its subclass.
40) `super()` function, which accesses the superclass without needing to know its name and which used invoke superclass.
41) The `__repr__` method is a special method in Python used to define a string representation of the object. This method is particularly useful for debugging and logging.
42) The `__iter__` method is another special method that makes the class iterable. This means you can use the class in a loop or any other context that requires an iterable. THis needs either `__next__` function to make it usable in any iteration context or yield
```python
class Test:
    def __init__(self):
        self.i = 0

    def __iter__(self):
        print('iter')
        return self
    
    def __next__(self):
        print(f'next {self.i}')
        self.i += 1
        if self.i > 5:
            raise StopIteration

for i in Test():
    print(i)
```
39) Every python object has built-in property `__dict__` which lists the content of object.
40) Class variables are shared variable across all the instances(Objects) of that class and instance variables is a local variable to that instance and not shared with other instances of same class. Note : You can access class variable using instance or using class see below but if we create instance variable of same name as class variable then instance variable of same name as class variable will be masked by instance variable.
```python
class Demo:
    class_var = "shared_variable"

d1 = Demo()
d2 = Demo()
print(d1.class_var)
#shared_variable
print(Demo.class_var)
#shared_variable
d1.class_var = 'shadowing class variable'
print(d1.class_var)
#shadowing class variable

```
41) Generators are special functions that return an iterator object. Generators in python with yield statement may only be used inside functions. A function that contains a yield statement is called a generator function. A generator function is an ordinary function object in all respects. 

You can create a function and replace the return statement with yield and use the function to run in a loop with set of values.
```python
def countdown(n):
    while n > 0:
        yield n
        n -= 1

# Using the generator
for number in countdown(5):
    print(number)
```
Exmaple code : https://github.com/pavanc059/PythonCertification/blob/000caf85d6df65ec5e05fc9383a8ebc6e0edd4ca/Labs/OOP/Generators_learning.py#L25

42) Iterator Objects is regular python object(class instance) which implements `__iter__()` and `__next__()` methods which allows the objects to be used in for/in statements to loops. similar to Iterable interface in java.
43) Special Operations on python objects example '+' operator can work between 2 objects by implementing `__add__()` method
44) *args and **kwargs are spacial function parameters that unpacks function positional parameters and keywords parameters.
```python
def funTest(*args):
    print(f'args {args}')

def funTest2(**kwargs):
    print(f'Keyword args {kwargs}')
#you cna pass any number of arguments which will be passed as tuple to function
funTest(1, 2, 'test', 'xyz', 6)
# similarly you can pass keyword arguments t
funTest2(first=1, second=2)

```
45) ```lambda``` function are anonymous function with no definition. 
    syntax : 
    ```python 
    lambda argument1, argument, ...: #body or logic
    ```
46) ```map()``` : map function takes first argument as function and second argument should be any iterator. map will apply function to all of the values in iterator. but this map only maps the function but to evaluate the function to values we need pass map to list --> list(map()) 
    example :
    ```python
        map(lambda book: libraryatmain.add_publication(book), [book1, book2, book3, book4, book5]) # refer to LibrarySystem --> library_processing_system.py
        #output Add publication <map object at 0x000001A906265720>
        list(map(lambda book: libraryatmain.add_publication(book), [book1, book2, book3, book4, book5])) # refer to LibrarySystem --> library_processing_system.py)
        #output Add publication [(1, 'Python Programming'), (2, 'Java Programming'), (3, 'C++ Programming'), (4, 'JavaScript Programming'), (5, 'HTML Programming')]
    ```
47) Decorator functions are used to wrap any python function, class around. This wrapper function executes the actual function
    example :
    Following function has 3 level of wrapping if we need to capture arguments from actual function and also the arguments from wrapper.
    If actual function has no arguments then 2 level or function with argument and wrapper don't have any arguments 

    ```python
        def warehouse_decorator(material):
            def wrapper(our_function):
                def internal_wrapper(*args):
                    print('<strong>*</strong> Wrapping items from {} with {}'.format(our_function.__name__, material))
                    our_function(*args)
                    print()
                return internal_wrapper
            return wrapper

        @warehouse_decorator('kraft')
        def pack_books(*args):
            print("We'll pack books:", args)

        #output
        #<strong>*</strong> Wrapping items from pack_books with kraft
        #We'll pack books: ('Alice in Wonderland', 'Winnie the Pooh')

        # 2 level with no argument function 
        def warehouse_decorator(material):
            def wrapper(our_function):       
                    print('<strong>*</strong> Wrapping items from {} with {}'.format(our_function.__name__, material))
                    return our_function                   
            return wrapper

        @warehouse_decorator('kraft')
        def pack_books():
            print("We'll pack books:")
        #output
        #<strong>*</strong> Wrapping items from pack_books with kraft
        #We'll pack books:
    ```
48) To print full trace of exception you can use `format_tb()`  function from traceback module which returns list of strings describing the traceback or `print_tb()` function from traceback module
49) To compare 2 variables are referring to same object we should use 'is' operator to compare values objects/variables holding use '=='
50) You can create a class without defining using `type(classname, (parentClass,), {attributes:values})` 

example: 
```python
def bark(self):
    print('Woof, woof')

class Animal:
    def feed(self):
        print('It is feeding time!')

Dog = type('Dog', (Animal, ), {'age':0, 'bark':bark})

print('The class name is:', Dog.__name__)
print('The class is an instance of:', Dog.__class__)
print('The class is based on:', Dog.__bases__)
print('The class attributes are:', Dog.__dict__)

doggy = Dog()
doggy.feed()
doggy.bark()
```
48) Metaclasses usually implement these two methods (`__init__`, `__new__`), taking control of the procedure of creating and initializing a new class instance. Classes receive a new layer of logic.
49) Using meta class you can equip any class with domain specific rules like all class by default it inherit from type/object class you can define meta class as base for new class
example :
```python
def greetings(self):
    print('Just a greeting function, but it could be something more serious like a check sum')

class My_Meta(type):
    def __new__(mcs, name, bases, dictionary):
        if 'greetings' not in dictionary:
            dictionary['greetings'] = greetings
        obj = super().__new__(mcs, name, bases, dictionary)
        return obj

class My_Class1(metaclass=My_Meta):
    pass

class My_Class2(metaclass=My_Meta):
    def greetings(self):
        print('We are ready to greet you!')

myobj1 = My_Class1()
myobj1.greetings()
myobj2 = My_Class2()
myobj2.greetings()

#output
# Just a greeting function, but it could be something more serious like a check sum
# We are ready to greet you!
```
50) Do not use mutable objects like list, dictionary or set as default argument value. Default arguments are evaluated when the function is defined, not when it's called. You can see below issue items list is shared between to invocation 
```python
# Problematic code with mutable default argument
def add_item(item, items=[]):  # BAD: mutable default argument
    items.append(item)
    return items

print(add_item(1))  # Output: [1]
print(add_item(2))  # Output: [1, 2]  <- Unexpected! We might expect [2]

#Corrected code 
def add_item(item, items=None):
    items = items if items is not None else []   
    items.append(item)
    return items

print(add_item(1))  # Output: [1]
print(add_item(2))  # Output: [2]  <- Unexpected! We might expect [2]

```
