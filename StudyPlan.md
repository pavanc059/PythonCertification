# PCPP1™ – Certified Professional in Python Programming 1

**Exam PCPP-32-10x – EXAM SYLLABUS**

## PCPP-32-101 Exam

**Status:** Live & Active  
**Last updated:** March 11, 2022  
**Aligned with:** Exam PCPP-32-101

### Exam Structure

The exam consists of five sections:

| Section | Items | Max Raw Score | Percentage |
|---------|-------|---------------|------------|
| Section 1 | 15 items | 42 | 35% |
| Section 2 | 7 items | 14 | 12% |
| Section 3 | 8 items | 24 | 20% |
| Section 4 | 8 items | 22 | 18% |
| Section 5 | 7 items | 18 | 15% |

---

## Section 1: Advanced Object-Oriented Programming (35%)

**Objectives covered by the block (15 exam items)**

### PCPP-32-101 1.1 – Understand and explain the basic terms and programming concepts used in the OOP paradigm - completed

- Essential terminology: class, instance, object, attribute, method, type, instance and class variables, superclasses and subclasses
- Reflexion: `isinstance()`, `issubclass()`
- The `__init__()` method
- Creating classes, methods, and class and instance variables; calling methods; accessing class and instance variables

### PCPP-32-101 1.2 – Perform Python core syntax operations - completed

- Python core syntax expressions – magic methods [Magic Methods](https://realpython.com/courses/magic-methods-classes/):
  - Comparison methods (e.g. `__eq__(self, other)`, `__lt__`, `__le__`, `__gt__`, `__ge__`, `__ne__`)
  - Numeric methods (e.g. `__abs__(self)`, `__add__`, `__sub__`, `__mul__`, `__truediv__`, `__floordiv__`, `__mod__`, `__pow__`)
  - Type conversion methods (e.g. `__int__`, `__float__`, `__str__`, `__bool__`)
  - Object intro- and retrospection (e.g. `__str__(self)`, `__repr__`, `__instancecheck__(self, object)`)
  - Object attribute access (e.g. `__getattr__(self, attribute)`, `__setattr__`, `__delattr__`, `__getattribute__`)
  - Accessing containers (e.g. `__getitem__(self, key)`, `__setitem__`, `__delitem__`, `__len__`, `__contains__`)
  - Context managers (e.g. `__enter__`, `__exit__`)
  - Callable objects (e.g. `__call__`)
  - Hashing and comparison (e.g. `__hash__`)
- Operating with special methods [Operator overloading/ method overloading](https://realpython.com/operator-function-overloading/)
- Extending class implementations to support additional core syntax operations

### PCPP-32-101 1.3 – Understand and use the concepts of inheritance, polymorphism, and composition - not started

- Class hierarchies
- Single vs. multiple inheritance
- Method Resolution Order (MRO)
- The `super()` function and cooperative inheritance
- Diamond problem and its resolution
- Duck typing
- Inheritance vs. composition
- Modelling real-life problems using the "is a" and "has a" relations
- Mixins and their usage patterns

[All above concepts](https://realpython.com/courses/inheritance-composition-python/)

### PCPP-32-101 1.4 – Understand the concept of extended function argument syntax and demonstrate proficiency in using decorators - not started

- Special identifiers: `*args`, `**kwargs`
- Forwarding arguments to other functions
- Function parameter handling: positional, keyword, default, positional-only, keyword-only
- Closures and variable scope (LEGB rule)
- Function and class decorators
- Decorating functions with classes
- Creating decorators and operating with them: implementing decorator patterns, decorator arguments, wrappers
- Decorator stacking
- Syntactic sugar
- Special methods: `__call__`, `__init__`
- `functools.wraps` for preserving function metadata
- Parameterized decorators
  
[All above concepts](https://realpython.com/learning-paths/functional-programming/)

### PCPP-32-101 1.5 – Design, build, and use Python static and class methods - In-complete

- Implementing class and static methods
- Class vs. static methods
- The `cls` parameter
- The `@classmethod` and `@staticmethod` decorators [Methods](https://realpython.com/courses/python-method-types/)
- Class methods: accessing and modifying the state/methods of a class, creating objects
- Alternative constructors using class methods
- Factory patterns with class methods ([Implementing the Factory Method Pattern](https://realpython.com/courses/factory-method-pattern/))

### PCPP-32-101 1.6 – Understand and use Python abstract classes and methods - In-complete

- Abstract classes and abstract methods: defining, creating, and implementing abstract classes and abstract methods
- The `abc` module: `ABC`, `abstractmethod`, `abstractproperty`
- Overriding abstract methods
- Implementing a multiple inheritance from abstract classes
- Delivering multiple child classes
- Abstract properties and static methods
- Interface design using abstract base classes
  
[Above topics brush up](https://realpython.com/courses/python-class-inheritance/)

### PCPP-32-101 1.7 – Understand and use the concept of attribute encapsulation - completed

- Definition, meaning, usage
- Name mangling with double underscore prefix
- Public, protected, and private attributes (conventions)
- Operating with the getter, setter, and deleter methods
- The `@property` decorator
- Property objects and descriptors
- Read-only and write-only properties

[Above topic complete reference](https://realpython.com/courses/property-python/)

### PCPP-32-101 1.8 – Understand and apply the concept of subclassing built-in classes - not started 

- Inheriting properties from built-in classes
- Using the concept of subclassing the built-ins to extend class features and modify class methods and attributes
- Subclassing `list`, `dict`, `str`, `int`, and other built-ins
- Overriding built-in methods
- `collections.UserDict`, `collections.UserList`, `collections.UserString` as alternatives
  
[Above topic completed refernce ](https://realpython.com/learning-paths/classic-data-structures-and-algorithms-with-python/)

### PCPP-32-101 1.9 – Demonstrate proficiency in the advanced techniques for creating and serving exceptions - not started 

- Exceptions as objects, named attributes of exception objects, basic terms and concepts
- Creating custom exception classes
- Exception hierarchy and inheritance
- Chained exceptions, the `__context__` and `__cause__` attributes, implicitly and explicitly chained exceptions
- Using `raise ... from ...` syntax
- Analyzing exception traceback objects, the `__traceback__` attribute
- Operating with different kinds of exceptions
- Exception groups (Python 3.11+)
- Best practices for exception handling

[Above topics complete reference](https://realpython.com/learning-paths/exception-handling-logging-debugging/)

### PCPP-32-101 1.10 – Demonstrate proficiency in performing shallow and deep copy operations - not started 

- Shallow and deep copies of objects
- Object: label vs. identity vs. value
- The `id()` function and the `is` operand
- Operating with the `copy()` and `deepcopy()` methods
- The `copy` module
- Customizing copy behavior with `__copy__` and `__deepcopy__`
- Mutable vs. immutable objects in copying

[Above topics reference](https://realpython.com/courses/deep-vs-shallow-copies/)

### PCPP-32-101 1.11 – Understand and perform (de)serialization of Python objects - not started 

- Object persistence, serialization and deserialization: meaning, purpose, usage
- Serializing objects as a single byte stream: the `pickle` module, pickling various data types
- The `dumps()` and `loads()` functions
- The `dump()` and `load()` functions for file operations
- Pickle protocols and versions
- Security considerations with pickle
- Serializing objects by implementing a serialization dictionary: the `shelve` module, file modes, creating shelve objects
- Alternative serialization: `json`, `marshal`, `yaml`

[Above topic reference](https://realpython.com/learning-paths/standard-library-modules-you-should-know/)

### PCPP-32-101 1.12 – Understand and explain the concept of metaprogramming - not started

- Metaclasses: meaning, purpose, usage
- The `type` metaclass and the `type()` function
- Creating classes dynamically with `type()`
- Special attributes: `__name__`, `__class__`, `__bases__`, `__dict__`, `__mro__`
- Operating with metaclasses, class variables, and class methods
- Defining custom metaclasses
- `__new__` vs. `__init__` in metaclasses
- Metaclass conflicts and resolution
- Practical use cases for metaclasses

[Above topics reference](https://realpython.com/learning-paths/metaprogramming-in-python/)
---

## Section 2: Coding Conventions, Best Practices, and Standardization (12%)

[Write more Pythonic code](https://realpython.com/learning-paths/writing-pythonic-code/)

**Objectives covered by the block (7 exam items)** 

### PCPP-32-101 2.1 – Understand and explain the concept of Python Enhancement Proposals and Python philosophy

- The PEP concept and selected PEPs: PEP 1, PEP 8, PEP 20, PEP 257
- PEP 1: different types of PEPs, formats, purpose, guidelines
- PEP 20: Python philosophy, its guiding principles, and design; the `import this` instruction and PEP 20 aphorisms
- Other important PEPs: PEP 484 (Type Hints), PEP 3107 (Function Annotations)

### PCPP-32-101 2.2 – Employ the PEP 8 guidelines, coding conventions, and best practices

- PEP 8 compliant checkers: `pylint`, `flake8`, `pycodestyle`
- Recommendations for code layout: indentation, continuation lines, maximum line length, line breaks, blank lines (vertical whitespaces)
- Default encodings
- Module imports: order, grouping, absolute vs. relative imports
- Recommendations for string quotes, whitespace, and trailing commas: single-quoted vs. double-quoted strings, whitespace in expressions and statements, whitespace and trailing commas
- Recommendations for using comments: block comments, inline comments
- Documentation strings
- Naming conventions: naming styles, recommendations (snake_case, PascalCase, UPPER_CASE)
- Programming recommendations: comparisons, boolean checks, exception handling

### PCPP-32-101 2.3 – Employ the PEP 257 guidelines, conventions, and best practices

- Docstrings: rationale, usage
- Comments vs. docstrings
- PEP 484 and type hints
- Creating, using, and accessing docstrings
- One-line vs. multi-line docstrings
- Documentation standards: Sphinx, reStructuredText, Google style, NumPy style
- Linters: `pydocstyle`, `darglint`
- Fixers: `black`, `autopep8`, `isort`

---

## Section 3: GUI Programming (20%)

**Objectives covered by the block (8 exam items)**

[Refer this course](https://realpython.com/learning-paths/python-gui-programming/)

### PCPP-32-101 3.1 – Understand and explain the basic concepts and terminology related to GUI programming

- GUI: meaning, rationale, basic terms and definitions
- Visual programming: examples, basic features
- Widgets/controls – basic terms: windows, title and title bars, buttons, icons, labels, etc.
- Classical vs. event-driven programming
- Events – basic terms
- Widget toolkits/GUI toolkits: tkinter, PyQt, Kivy

### PCPP-32-101 3.2 – Use GUI toolkits, basic blocks, and conventions to design and build simple GUI applications

- Importing tkinter components
- Creating an application's main window: the `Tk()`, `mainloop()`, and `title()` methods
- Adding widgets to the window: buttons, labels, frames, the `place()` method, widget constructors, location, screen coordinates, size, etc.
- Launching the event controller: event handlers, defining and using callbacks, the `destroy()` method, dialog boxes
- Shaping the main window and interacting with the user
- Checking the validity of user input and handling errors
- Working with Canvas and its methods
- Using the Entry, Radiobutton, and Button widgets
- Managing widgets with the grid and place managers
- Binding events using the `bind()` method
- Menu bars and popup menus
- Message boxes and file dialogs

### PCPP-32-101 3.3 – Demonstrate proficiency in using widgets and handling events

- Settling widgets in the window's interior, geometry managers
- Coloring widgets, color modes: RGB, HEX
- Event handling: writing event handlers and assigning them to widgets
- Event-driven programming: implementing interfaces using events and callbacks
- Widget properties and methods
- Variables: observable variables and adding observers to variables
- Using selected clickable and non-clickable widgets
- Identifying and servicing GUI events
- Keyboard and mouse events
- Widget styling and themes

---

## Section 4: Network Programming (18%)

**Objectives covered by the block (8 exam items)**

[Refer to this course](https://realpython.com/learning-paths/network-programming-and-security/)

### PCPP-32-101 4.1 – Understand and explain the basic concepts of network programming

- REST: principles, constraints, statelessness
- Network sockets: TCP, UDP
- Domains, addresses, ports, protocols, and services
- Network communication: connection-oriented vs. connectionless communication, clients and servers
- OSI model basics
- HTTP/HTTPS protocols

### PCPP-32-101 4.2 – Demonstrate proficiency in working with sockets in Python

- The `socket` module: importing and creating sockets
- Socket types: `SOCK_STREAM`, `SOCK_DGRAM`
- Connecting sockets to HTTP servers, closing connections with servers
- Binding and listening for connections
- Accepting client connections
- Sending requests to servers, the `send()` and `sendall()` methods
- Receiving responses from servers, the `recv()` method
- Exception handling mechanisms and exception types
- Non-blocking sockets and timeouts

### PCPP-32-101 4.3 – Employ data transfer mechanisms for network communication

- JSON: syntax, structure, data types (numbers, strings, Boolean values, null), compound data (arrays and objects), sample JSON documents and their anatomies
- The `json` module: serialization and deserialization, serializing Python data/deserializing JSON (the `dumps()` and `loads()` methods), serializing and deserializing Python objects
- Custom JSON encoders and decoders
- XML: syntax, structure, sample XML documents and their anatomies, DTD, XML as a tree
- Processing XML files: `xml.etree.ElementTree`, `xml.dom`, `lxml`
- YAML and other data formats

### PCPP-32-101 4.4 – Design, develop, and improve a simple REST client

- The `requests` module: installation and basic usage
- Designing, building, and using testing environments
- HTTP methods: GET, POST, PUT, DELETE, PATCH
- CRUD operations
- Adding and updating data
- Fetching and removing data from servers
- Analyzing the server's response
- Response status codes: 2xx, 3xx, 4xx, 5xx
- Headers and authentication
- Query parameters and request bodies
- Session management
- Error handling and retries

---

## Section 5: File Processing and Communicating with a Program's Environment (15%)

**Objectives covered by the block (7 exam items)**
[Refer these course](https://realpython.com/learning-paths/files-and-file-streams-in-python/)
[Refer these course](https://realpython.com/learning-paths/database-access-in-python/)

### PCPP-32-101 5.1 – Demonstrate proficiency in database programming in Python

- The `sqlite3` module
- Creating and closing database connection using the `connect()` and `close()` methods
- Context managers for database connections
- Creating tables with proper data types
- Inserting, reading, updating, and deleting data
- Transaction demarcation: `commit()`, `rollback()`
- Cursor methods: `execute()`, `executemany()`, `fetchone()`, `fetchall()`, `fetchmany()`
- Creating basic SQL statements (SELECT, INSERT INTO, UPDATE, DELETE, etc.)
- SQL injection prevention with parameterized queries
- Indexes and query optimization
- Working with other databases: MySQL, PostgreSQL (using appropriate drivers)

### PCPP-32-101 5.2 – Demonstrate proficiency in processing different file formats in Python

- Parsing XML documents
- Searching data in XML documents using the `find()` and `findall()` methods
- Building XML documents using the `Element` class and the `SubElement()` function
- XML namespaces and attributes
- Reading and writing CSV data using functions and classes: `reader`, `writer`, `DictReader`, `DictWriter`
- CSV dialects and custom delimiters
- Logging events in applications: the `logging` module
- Working with different levels of logging: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Using LogRecord attributes to create log formats
- Creating custom handlers and formatters
- File handlers, stream handlers, rotating file handlers
- Logger hierarchy and propagation
- Parsing and creating configuration files using the `ConfigParser` object
- Interpolating values in .ini files
- JSON and YAML configuration files

---

## Section 6: Advanced Python Concepts (Supplementary)

**Additional topics for comprehensive professional certification preparation**
[Course link](https://realpython.com/learning-paths/python-concurrency-parallel-programming/)

### 6.1 – Understand and implement concurrency and parallelism

- Threading: the `threading` module
  - Thread class: creating and starting threads
  - Thread synchronization: Lock, RLock, Semaphore, Event, Condition
  - Thread-local data
  - Daemon threads
- Multiprocessing: the `multiprocessing` module
  - Process class: creating and managing processes
  - Inter-process communication: Queue, Pipe
  - Process pools: Pool class, map, apply
  - Shared memory and Manager
- Asyncio: asynchronous programming
  - `async` and `await` syntax
  - Event loops and coroutines
  - Tasks and futures
  - `asyncio.gather()`, `asyncio.wait()`
  - Asynchronous context managers and iterators
- Global Interpreter Lock (GIL)
  - Understanding GIL limitations
  - When to use threading vs. multiprocessing
  - CPU-bound vs. I/O-bound operations
- Concurrent.futures module
  - ThreadPoolExecutor and ProcessPoolExecutor
  - Future objects

### 6.2 – Master context managers

- The `with` statement and its benefits
- Context manager protocol: `__enter__()` and `__exit__()` methods
- Creating custom context managers
- The `contextlib` module
  - `@contextmanager` decorator
  - `closing()`, `suppress()`, `redirect_stdout()`, `redirect_stderr()`
  - `ExitStack` for managing multiple context managers
- Asynchronous context managers: `__aenter__()` and `__aexit__()`

### 6.3 – Demonstrate proficiency with generators and iterators

[Course link](https://realpython.com/learning-paths/generators-and-generator-expressions/)

- Iterator protocol: `__iter__()` and `__next__()`
- Creating custom iterators
- Generator functions and the `yield` keyword
- Generator expressions
- `yield from` for delegating to sub-generators
- Generator methods: `send()`, `throw()`, `close()`
- The `itertools` module
  - Infinite iterators: `count()`, `cycle()`, `repeat()`
  - Finite iterators: `chain()`, `compress()`, `dropwhile()`, `takewhile()`
  - Combinatoric iterators: `product()`, `permutations()`, `combinations()`
- Memory efficiency with generators
- Coroutines and generator-based concurrency

### 6.4 – Work with regular expressions
[Course link](https://realpython.com/learning-paths/standard-library-modules-you-should-know/)

- The `re` module: importing and basic usage
- Pattern matching: `match()`, `search()`, `findall()`, `finditer()`
- Pattern substitution: `sub()`, `subn()`
- Splitting strings: `split()`
- Compiling patterns: `re.compile()`
- Pattern syntax and metacharacters: `.`, `^`, `$`, `*`, `+`, `?`, `[]`, `|`, `()`
- Character classes and escape sequences
- Groups and capturing: numbered groups, named groups
- Non-capturing groups and lookahead/lookbehind assertions
- Flags: `re.IGNORECASE`, `re.MULTILINE`, `re.DOTALL`, `re.VERBOSE`
- Raw strings for patterns

### 6.5 – Implement comprehensive testing strategies
[Course link](https://realpython.com/learning-paths/test-your-python-apps/)

- The `unittest` module
  - TestCase class and test methods
  - Assertions: `assertEqual()`, `assertTrue()`, `assertRaises()`, etc.
  - Test fixtures: `setUp()`, `tearDown()`, `setUpClass()`, `tearDownClass()`
  - Test suites and test runners
  - Skipping tests and expected failures
- The `pytest` framework
  - Writing test functions
  - Fixtures and dependency injection
  - Parametrized tests
  - Markers and plugins
- Mocking and patching
  - The `unittest.mock` module
  - Mock objects and MagicMock
  - `patch()` decorator and context manager
  - Assertions on mock calls
- Test-driven development (TDD) principles
- Code coverage tools: `coverage.py`
- Integration and end-to-end testing

### 6.6 – Manage virtual environments and packages
[Course link](https://realpython.com/learning-paths/perfect-your-python-development-setup/)

- Virtual environments: purpose and benefits
- The `venv` module: creating and activating virtual environments
- `virtualenv` as an alternative
- Package management with `pip`
  - Installing packages: `pip install`
  - Upgrading and uninstalling: `pip install --upgrade`, `pip uninstall`
  - Requirements files: `requirements.txt`, `pip freeze`
  - Installing from version control
- Package distribution
  - `setup.py` and `setuptools`
  - Package structure and metadata
  - Building distributions: sdist, wheel
  - Uploading to PyPI
- Modern packaging with `pyproject.toml`
  - PEP 517 and PEP 518
  - Build backends: `setuptools`, `flit`, `poetry`
- Dependency management tools: `pipenv`, `poetry`

### 6.7 – Optimize performance and profile code

[Course link](https://realpython.com/learning-paths/understand-cpython/)

- Performance profiling
  - The `cProfile` module: profiling function calls
  - The `profile` module
  - Analyzing profiler output
- Timing code execution
  - The `timeit` module: measuring execution time
  - `time.perf_counter()` for high-resolution timing
- Memory profiling
  - The `tracemalloc` module
  - Memory usage analysis
  - Finding memory leaks
- Optimization techniques
  - List comprehensions vs. loops
  - Generator expressions for memory efficiency
  - Built-in functions: `map()`, `filter()`, `reduce()`
  - `functools.lru_cache` for memoization
  - Using appropriate data structures
  - Avoiding premature optimization
- Algorithmic complexity: Big O notation basics

### 6.8 – Apply type hints and static type checking

- PEP 484: Type Hints
- Basic type annotations: `int`, `str`, `float`, `bool`
- The `typing` module
  - Generic types: `List`, `Dict`, `Set`, `Tuple`
  - Optional types: `Optional`, `Union`
  - Callable types: `Callable`
  - Type variables: `TypeVar`
  - Generic classes and functions
  - Protocol and structural subtyping
  - Literal types and Final
- Function annotations and return types
- Variable annotations
- Type aliases
- Static type checkers
  - `mypy`: installation and usage
  - Type checking configuration
  - Gradual typing
- Benefits of type hints: documentation, IDE support, error detection

### 6.9 – Work with advanced data structures

- Collections module
  - `namedtuple`: creating tuple subclasses with named fields
  - `deque`: double-ended queue
  - `Counter`: counting hashable objects
  - `OrderedDict`: dictionary with order preservation
  - `defaultdict`: dictionary with default values
  - `ChainMap`: combining multiple dictionaries
- Data classes: the `dataclasses` module
  - `@dataclass` decorator
  - Field definitions and default values
  - Immutable data classes
  - Post-init processing
- Enumerations: the `enum` module
  - Creating enums
  - Enum members and values
  - Auto-numbering
- Heaps: the `heapq` module
- Bisect: the `bisect` module for sorted lists

### 6.10 – Understand functional programming concepts

- First-class functions
- Higher-order functions
- Lambda expressions
- Built-in functional tools
  - `map()`, `filter()`, `reduce()`
  - `zip()`, `enumerate()`
- The `functools` module
  - `partial()`: partial function application
  - `reduce()`: cumulative operations
  - `lru_cache()`: memoization
  - `wraps()`: decorator helper
  - `singledispatch()`: single-dispatch generic functions
- The `operator` module
- Immutability and pure functions
- Function composition

### 6.11 – Handle dates, times, and timezones

- The `datetime` module
  - `date`, `time`, `datetime` objects
  - Creating and manipulating dates and times
  - Formatting with `strftime()`
  - Parsing with `strptime()`
  - Timedeltas for time arithmetic
- The `time` module
  - Unix timestamps
  - `sleep()` for delays
- Timezone handling
  - The `zoneinfo` module (Python 3.9+)
  - Timezone-aware vs. naive datetime objects
  - UTC and local time conversions
- The `calendar` module

### 6.12 – Work with command-line interfaces

- The `sys` module
  - `sys.argv` for command-line arguments
  - `sys.stdin`, `sys.stdout`, `sys.stderr`
  - `sys.exit()` for program termination
- The `argparse` module
  - Creating argument parsers
  - Positional and optional arguments
  - Argument types and validation
  - Subcommands
  - Help messages
- The `os` module
  - Environment variables: `os.environ`
  - File and directory operations
  - Path manipulation
- The `pathlib` module
  - Path objects and operations
  - Cross-platform path handling
- The `subprocess` module
  - Running external commands
  - Capturing output
  - Pipes and redirection

---

## Study Resources

- Official Python Documentation: https://docs.python.org/3/
- Python Institute: https://pythoninstitute.org/
- Real Python: https://realpython.com/
- Python Enhancement Proposals (PEPs): https://peps.python.org/
- Practice platforms: LeetCode, HackerRank, Codewars
