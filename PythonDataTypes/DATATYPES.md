# Variables in Python

**A variable comes into existence as a result of assigning a value to it** . Unlike in other languages, you don't need to declare it in any special way.

If you assign any value to a nonexistent variable, the variable will be  **automatically created** . You don't need to do anything else.

### **give a name to a variable :**

you must follow some strict rules:

* the name of the variable must be composed of upper-case or lower-case letters, digits, and the character `_` (underscore)
* the name of the variable must begin with a letter;
* the underscore character is a letter;
* upper- and lower-case letters are treated as different (a little differently than in the real world - *Alice* and *ALICE* are the same first names, but in Python they are two different variable names, and consequently, two different variables);
* the name of the variable must not be any of Python's reserved words (the keywords - we'll explain more about this soon).


### Variable assignment with shortend :

example : a = 6|b = 3|a /= 2 * b in this expression python first evaluates value after equals and then assign to value i.e 2 * b = 6 | a = 6 → 6 / 6 = 1.0


| Example                                     | Data Type  |
| ------------------------------------------- | ---------- |
| x = "Hello World"                           | str        |
| x = 20                                      | int        |
| x = 20.5                                    | float      |
| x = 1j                                      | complex    |
| x = ["apple", "banana", "cherry"]           | list       |
| x = ("apple", "banana", "cherry")           | tuple      |
| x = range(6)                                | range      |
| x = {"name" : "John", "age" : 36}           | dict       |
| x = {"apple", "banana", "cherry"}           | set        |
| x = frozenset({"apple", "banana","cherry"}) | frozenset  |
| x = True                                    | bool       |
| x = b"Hello"                                | bytes      |
| x = bytearray(5)                            | bytearray  |
| x = memoryview(bytes(5))                    | memoryview |
| x = None                                    | NoneType   |
