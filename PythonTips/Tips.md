1) By default Python uses UTF-8 encoding to change default encoding you need to insert below comment line with encoding scheem

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
7) In python 2 == 2. (True)
8) Operator priority table

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
9) Variable assignment in python can also be done as following ways

   1) x = y = z = 5
   2) x, y, z = 5, 10, 20
10) while loop in python can have else condition which executes when you while condition body don't execute
    [syntax] : while condition:
    #while_body
    else:
    #else_condition body
11) else in for loop executes at the end of for execution
    [syntax] : for variable in range(value):
    #for_body
    else:
    #else block the executes at end of for loop
12) logical operators and bit wise operators in python. logical operators operate on final value of the expression but bit wise operators work on each bit as example below
    [Example] : i = 15; j = 22
    print(i and j) : 22
    print(i & j)   : 6
    print(j and i) : 15
    print(j & i)   : 6
13) list in python can store list of value of different types as shown below
    numbers = [10, [2,4,6], 7, 2.0, 'test']
14) swapping elements in python is simpler than swapping elements in java without creating third variable
    variable1, variable2 = variable2, variable1
15) when you copy a variable to another variable it copies the content of the variable(scalar variable) but with list when you copy one list to another it copies memory address of the list
    modifying one list can effect other list. TO actually copy list python has a syntax called slice
    [syntax] my_list[start:end] : Note end value should be last element index -1  that you wish to copy

    - start is the index of the first element included in the slice;
    - end is the index of the first element not included in the slice.
      [example] list1 = [1,2] \n list2 = [:]
16) list comprehension a special syntax used by python to fill large list
    [examples] : list = [value for i in range(8)] - this fills list with value from 0 to 7 indexes
    list2 = [x ** 2 for x in range(10)] - this used x value from for loop and substitute in calculation which results (0, 1, 4, 9,16,25, 36, 49, 64, 81)list3 = [2 ** i for i in range(8)] - (1, 2, 4, 8, 16, 32, 64, 128)
    list4 = [x for x in list2 if x % 2 != 0 ] - you can also include if condition before filling the list in python this list will contain all odd numbers
17) Python built-in functions :https://docs.python.org/3/library/functions.html

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
18) Python offers another convention for passing arguments, where the meaning of the argument is dictated by its name, not by its position - it's called keyword argument passing
19) Passing arguments to a function rule You can mix positional and keyword arguments fashions if you want - there is only one unbreakable rule: you have to put positional arguments before keyword arguments.
20) None keyword used for assign it to a variable (or return it as a function's result) or when you compare it with a variable to diagnose its internal state.
21) int() function converts string to integer/number we can pass second argument to convert given string formatted number to binary (2), hexa (16) or Octa (10) => Ex int("10", 2) = 2, int("A", 16) = 10

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
