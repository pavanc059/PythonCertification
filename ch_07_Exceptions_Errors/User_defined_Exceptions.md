## User Defined exceptions
Exceptions are classes. Furthermore, when an exception is raised, an object of the class is instantiated, and goes through all levels of program execution, looking for the except branch that is prepared to deal with it.

- Such an object carries some useful information which can help you to precisely identify all aspects of the pending situation. To achieve that goal, Python offers a special variant of the exception clause

```python
try:
    i = int("Hello!")
except Exception as e:
    print(e)
    print(e.__str__())
```
- All the built-in Python exceptions form a hierarchy of classes. There is no obstacle to extending it if you find it reasonable.

```python
#This program dumps all predefined exception classes in the form of a tree-like printout.
def printExcTree(thisclass, nest = 0):
    if nest > 1:
        print("   |" * (nest - 1), end="")
    if nest > 0:
        print("   +---", end="")

    print(thisclass.__name__)

    for subclass in thisclass.__subclasses__():
        printExcTree(subclass, nest + 1)

printExcTree(BaseException)

Output :
BaseException
   +---Exception
   |   +---TypeError
   |   +---StopAsyncIteration
   |   +---StopIteration
   |   +---ImportError
   |   |   +---ModuleNotFoundError
   |   |   +---ZipImportError
   |   +---OSError
   |   |   +---ConnectionError
   |   |   |   +---BrokenPipeError
   |   |   |   +---ConnectionAbortedError
   |   |   |   +---ConnectionRefusedError
   |   |   |   +---ConnectionResetError
   |   |   +---BlockingIOError
   |   |   +---ChildProcessError
   |   |   +---FileExistsError
   |   |   +---FileNotFoundError
   |   |   +---IsADirectoryError
   |   |   +---NotADirectoryError
   |   |   +---InterruptedError
   |   |   +---PermissionError
   |   |   +---ProcessLookupError
   |   |   +---TimeoutError
   |   |   +---UnsupportedOperation
   |   |   +---herror
   |   |   +---gaierror
   |   |   +---timeout
   |   |   +---Error
   |   |   |   +---SameFileError
   |   |   +---SpecialFileError
   |   |   +---ExecError
   |   |   +---ReadError
   |   +---EOFError
   |   +---RuntimeError
   |   |   +---RecursionError
   |   |   +---NotImplementedError
   |   |   +---_DeadlockError
   |   |   +---BrokenBarrierError
   |   +---NameError
   |   |   +---UnboundLocalError
   |   +---AttributeError
   |   +---SyntaxError
   |   |   +---IndentationError
   |   |   |   +---TabError
   |   +---LookupError
   |   |   +---IndexError
   |   |   +---KeyError
   |   |   +---CodecRegistryError
   |   +---ValueError
   |   |   +---UnicodeError
   |   |   |   +---UnicodeEncodeError
   |   |   |   +---UnicodeDecodeError
   |   |   |   +---UnicodeTranslateError
   |   |   +---UnsupportedOperation
   |   +---AssertionError
   |   +---ArithmeticError
   |   |   +---FloatingPointError
   |   |   +---OverflowError
   |   |   +---ZeroDivisionError
   |   +---SystemError
   |   |   +---CodecRegistryError
   |   +---ReferenceError
   |   +---BufferError
   |   +---MemoryError
   |   +---Warning
   |   |   +---UserWarning
   |   |   +---DeprecationWarning
   |   |   +---PendingDeprecationWarning
   |   |   +---SyntaxWarning
   |   |   +---RuntimeWarning
   |   |   +---FutureWarning
   |   |   +---ImportWarning
   |   |   +---UnicodeWarning
   |   |   +---BytesWarning
   |   |   +---ResourceWarning
   |   +---error
   |   +---Verbose
   |   +---Error
   |   +---TokenError
   |   +---StopTokenizing
   |   +---Empty
   |   +---Full
   |   +---_OptionError
   |   +---TclError
   |   +---SubprocessError
   |   |   +---CalledProcessError
   |   |   +---TimeoutExpired
   |   +---Error
   |   |   +---NoSectionError
   |   |   +---DuplicateSectionError
   |   |   +---DuplicateOptionError
   |   |   +---NoOptionError
   |   |   +---InterpolationError
   |   |   |   +---InterpolationMissingOptionError
   |   |   |   +---InterpolationSyntaxError
   |   |   |   +---InterpolationDepthError
   |   |   +---ParsingError
   |   |   |   +---MissingSectionHeaderError
   |   +---InvalidConfigType
   |   +---InvalidConfigSet
   |   +---InvalidFgBg
   |   +---InvalidTheme
   |   +---EndOfBlock
   |   +---BdbQuit
   |   +---error
   |   +---_Stop
   |   +---PickleError
   |   |   +---PicklingError
   |   |   +---UnpicklingError
   |   +---_GiveupOnSendfile
   |   +---error
   |   +---LZMAError
   |   +---RegistryError
   |   +---ErrorDuringImport
   +---GeneratorExit
   +---SystemExit
   +---KeyboardInterrupt
```
- The exceptions hierarchy is neither closed nor finished, and you can always extend it if you want or need to create your own world populated with your own exceptions.
- It may be useful when you create a complex module which detects errors and raises exceptions, and you want the exceptions to be easily distinguishable from any others brought by Python.
- This is done by defining your own, new exceptions as subclasses derived from predefined ones.

`Note: if you want to create an exception which will be utilized as a specialized case of any built-in exception, derive it from just this one. If you want to build your own hierarchy, and don't want it to be closely connected to Python's exception tree, derive it from any of the top exception classes, like Exception.`

```python
class MyZeroDivisionError(ZeroDivisionError):	
	pass

def doTheDivision(mine):
	if mine:
		raise MyZeroDivisionError("some worse news")
	else:		
		raise ZeroDivisionError("some bad news")

for mode in [False, True]:
	try:
		doTheDivision(mode)
	except ZeroDivisionError:
		print('Division by zero')


for mode in [False, True]:
	try:
		doTheDivision(mode)
	except MyZeroDivisionError:
		print('My division by zero')
	except ZeroDivisionError:
		print('Original division by zero')
```
- The function is invoked four times in total, while the first two invocations are handled using only one except branch (the more general one) and 
the last two ones with two different branches, able to distinguish the exceptions (don't forget: the order of the branches makes a fundamental difference!)

```python
#### Custom exception classes that inherit from Exception base class
class InvalidAgeError(Exception):
    """Raised when age is not within valid range"""
    pass

class EmptyStringError(Exception):
    """Raised when required string is empty"""
    pass

class NegativeNumberError(Exception):
    """Raised when number is negative but must be positive"""
    pass

class InvalidEmailError(Exception):
    """Raised when email format is invalid"""
    pass

class DuplicateEntryError(Exception):
    """Raised when trying to add duplicate entry"""
    pass
```
#### Building user defined exceptions
```python
class PizzaError(Exception):
    def __init__(self, pizza, message):
        Exception.__init__(message)
        self.pizza = pizza	


class TooMuchCheeseError(PizzaError):
    def __init__(self, pizza, cheese, message):
        PizzaError._init__(self, pizza, message)
        self.cheese = cheese
```

- You can start building it by defining a general exception as a new base class for any other specialized exception. Like PizzaError
`Note: we're going to collect more specific information here than a regular Exception does, so our constructor will take two arguments:`
- one specifying a pizza as a subject of the process,
- and one containing a more or less precise description of the problem.
- we pass the second parameter to the superclass constructor, and save the first inside our own property.
- A more specific problem (like an excess of cheese) can require a more specific exception. It's possible to derive the new class from the already defined PizzaError class.
- The TooMuchCheeseError exception needs more information than the regular PizzaError exception, so we add it to the constructor - the name cheese is then stored for further processing.