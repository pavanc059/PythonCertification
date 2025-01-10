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
| x = 1j                                      | Complex : Complex numbers consist of a real part and an imaginary part, where the imaginary part is denoted by 'j' in Python (equivalent to 'i' in mathematics).   |
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

### Type Cast :

* The `int()` function **takes one argument** (e.g., a string: `int(string)`) and tries to convert it into an integer;
* The `float()` function takes one argument (e.g., a string: `float(string)`) and tries to convert it into a float.


‘10’ always represents the total number of digits in any base if you are writing the number in the respective number system. *But it’s only funny in binary.*

| Number System | Numbric value | Converted to Number systme value | number denotation                                   | Python function used to conver                                              |
| ------------- | ------------- | -------------------------------- | --------------------------------------------------- | --------------------------------------------------------------------------- |
| Binary        | 4             | 0b100                            | 0b (0's and 1's)                                    | bin(number) => gives binary format                                          |
| Hexadecimal   | 16            | 0x10 or 0xA                      | 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, A, B, C, D, E, and F. | hex() function to convert values to hexadecimal format for display purposes <br><br> Steps to convert decimal to hexa : <br> 1) Use modules operator '%' with value%16 and note reminder value as first value of hexadecimal value then multiple value*16 note value before decimal(".") <br> 2) Now follow above step replace actual value with value noted before decimal point <br> Example : <br> 64 in hexa -> 65%16 and reminder is 1 note 1 as first hexa value from right and now devide 65/16 = 4.0625 values before decial is 4 <br> now again find reminder of 4%16 which is 4 and 4/16 is 0.25 now we reach value befre decimal as 0 we can stop calculating further now and take both reminders final heax value of 65 is 0x41  |
| Octal         | 8             | 0o10                             | 0, 1, 2, 3, 4, 5, 6, 7                              | oct()                                                                      |
