# Python Advanced Exceptions

In this section, we will explore advanced concepts related to exceptions in Python, including custom exceptions, exception chaining, and context management.

When Python executes a script and encounters a situation that it cannot cope with, it:
-   stops your program;
-   creates a spacial kind of data called an exception. This exception is an object.
  
Both of these activities are called raising an exception. We can say that Python always raises an exception (or that an exception has been raised) when it has no idea what do to with your code.

What happens next?
- The raised exception expects somebody or something to notice it and take care of it;
- if nothing happens to take care of the raised exception, the program will be forcibly terminated, and you will see an error message sent to the console by Python;
- otherwise, if the exception is taken care of and handled properly, the suspended program can be resumed and its execution can continue.

Python provides effective tools that allow you to observe exceptions, identify them and handle them efficiently. This is possible due to the fact that all potential exceptions have their unambiguous names, so you can categorize them and react appropriately.

```python
try:
    print(int('a'))
except ValueError as e_variable:
    print(e_variable.args)

```
The except clause may specify a variable after the exception name. In this example it’s an e_variable. This variable is bound to an exception instance with the arguments stored in the args attribute of the e_variable object. Some exception objects carry additional information about the exception itself.

1) ImportError
```python
try:
    import abcdefghijk

except ImportError as e:
    print(e.args)
    print(e.name)
    print(e.path)

```
The ImportError exception – raised when the import statement has trouble trying to load a module. The attributes are:

  - name – represents the name of the module that was attempted to be imported;
  - path – represents the path to any file which triggered the exception, respectively. Could be None.

2) UnicodeError 

The UnicodeError exception – raised when a Unicode-related encoding or decoding error occurs. It is a subclass of ValueError.

The UnicodeError has attributes that describe an encoding or decoding error.

 - encoding – the name of the encoding that raised the error.
 - reason – a string describing the specific codec error.
 - object – the object the codec was attempting to encode or decode.
 - start – the first index of invalid data in the object.
 - end – the index after the last invalid data in the object.



## Custom Exceptions

Creating custom exceptions allows you to define error types that are specific to your application. This can make your code more readable and easier to debug.

```python
class CustomError(Exception):
    """Base class for other exceptions"""
    pass

class InputError(CustomError):
    """Raised when there is an error in the input"""
    pass

class CalculationError(CustomError):
    """Raised when a calculation fails"""
    pass
```

## Exception Chaining

Python 3 introduced a very interesting feature called 'Exception chaining' to effectively deal with exceptions. 

- Imagine a situation where you are already handling an exception and your code incidentally triggers an additional exception. Should your code lose the information about the previous exception? Of course not. So the information should be available to the code following the erroneous code. This is an example of implicit chaining.
- Another case pops up when we knowingly wish to handle an exception and translate it to another type of exception. Such a situation is typical when you have a good reason for the unifying behavior of one piece of code to act similarly to another piece of code, like a legacy code. In this situation it would also be nice to keep the details of the former exception. This is an example of explicit chaining.

This chaining concept introduces two attributes of exception instances: 
  - the `__context__` attribute, which is inherent for implicitly chained exceptions;
  - the `__cause__` attribute, which is inherent for explicitly chained exceptions.

```python
a_list = ['First error', 'Second error']

try:
    print(a_list[3])
except Exception as e:
    try:
        # the following line is a developer mistake - they wanted to print progress as 1/10	but wrote 1/0
        print(1 / 0)
    except ZeroDivisionError as f:
        print('Inner exception (f):', f)
        print('Outer exception (e):', e)
        print('Outer exception referenced:', f.__context__)
        print('Is it the same object:', f.__context__ is e)

#output :
# Inner exception (f): division by zero
# Outer exception (e): list index out of range
# Outer exception referenced: list index out of range
# Is it the same object: True
```
The original exception object e is now being referenced by the `__context__` attribute of the following exception f.

The except Exception clause is a wide one and normally should be used as a last resort to catch all unhandled exceptions. It’s so wide because we don’t know what kind of exception might occur.

So, when a subsequent exception (much better forecasted) occurs, we still can say a lot about the nature of the first exception.

Exception chaining allows you to link exceptions together, providing more context when an error occurs.


#### Advanced exception - explicitly chained excepetions

```python
try:
    raise ValueError("Initial error")
except ValueError as e:
    raise RuntimeError("Secondary error") from e
```

```python
class RocketNotReadyError(Exception):
    pass


def personnel_check():
    try:
        print("\tThe captain's name is", crew[0])
        print("\tThe pilot's name is", crew[1])
        print("\tThe mechanic's name is", crew[2])
        print("\tThe navigator's name is", crew[3])
    except IndexError as e:
        raise RocketNotReadyError('Crew is incomplete') from e

crew = ['John', 'Mary', 'Mike']
print('Final check procedure')

personnel_check()

#output
# Final check procedure

# 	The captain's name is John

# 	The pilot's name is Mary

# 	The mechanic's name is Mike

# Traceback (most recent call last):

#   File "main.py", line 10, in personnel_check

#     print("\tThe navigator's name is", crew[3])

# IndexError: list index out of range



# The above exception was the direct cause of the following exception:



# Traceback (most recent call last):

#   File "main.py", line 17, in <module>

#     personnel_check()

#   File "main.py", line 12, in personnel_check

#     raise RocketNotReadyError('Crew is incomplete') from e

# __main__.RocketNotReadyError: Crew is incomplete

# handling RocketNotReady exception
try:
    personnel_check()
except RocketNotReadyError as f:
    print('General exception: "{}", caused by "{}"'.format(f, f.__cause__))

#output
# Final check procedure

# 	The captain's name is John

# 	The pilot's name is Mary

# 	The mechanic's name is Mike

# General exception: "Crew is incomplete", caused by "list index out of range"

```

To convert an explicit type of exception object to another type of exception object at the moment when the second exception is occurring. 

- Imagine that your code is responsible for the final checking process before the rocket is launched. The list of checks is a long one, and different checks could result in different exceptions.
- But as it is a very serious process, you should be sure that all checks are passed. If any fails, it should be marked in the log book and re-checked next time.

#### traceback attribute
Each exception object owns a `__traceback__` attribute.

Python allows us to operate on the traceback details because each exception object (not only chained ones) owns a `__traceback__` attribute. 

```python
class RocketNotReadyError(Exception):
    pass


def personnel_check():
    try:
        print("\tThe captain's name is", crew[0])
        print("\tThe pilot's name is", crew[1])
        print("\tThe mechanic's name is", crew[2])
        print("\tThe navigator's name is", crew[3])
    except IndexError as e:
        raise RocketNotReadyError('Crew is incomplete') from e


crew = ['John', 'Mary', 'Mike']

print('Final check procedure')

try:
    personnel_check()
except RocketNotReadyError as f:
    print(f.__traceback__)
    print(type(f.__traceback__))

# output
# Final check procedure
# 	The captain's name is John
# 	The pilot's name is Mary
# 	The mechanic's name is Mike
# <traceback object at 0x7f3391c1e230>
# <class 'traceback'>

try:
    personnel_check()
except RocketNotReadyError as f:
    print('\nTraceback details')
    details = traceback.format_tb(f.__traceback__)
    print("\n".join(details))

#output
# Traceback details
#   File "main.py", line 22, in <module>
#     personnel_check()
#   File "main.py", line 14, in personnel_check
#     raise RocketNotReadyError('Crew is incomplete') from e
```
From the output presented on the previous page, we can conclude that we have to deal with a traceback type object.

- To achieve this, we could use the `format_tb()` method delivered by the built-in traceback module to get a list of strings describing the traceback.
- We could use the `print_tb()` method, also delivered by the traceback module, to print strings directly to the standard output. 

## Context Management

Using the `with` statement, you can manage resources more effectively and handle exceptions that occur within a block of code.

```python
class ManagedResource:
    def __enter__(self):
        print("Resource acquired")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            print(f"Exception: {exc_value}")
        print("Resource released")

with ManagedResource() as resource:
    raise ValueError("An error occurred")
```
