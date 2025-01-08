### Strings :
First of all, Python's strings are immutable sequences.
- The len() function used for strings returns a number of characters contained by the arguments.
- Any string can be empty. Its length is 0
- Don't forget that a backslash (\) used as an escape character is not included in the string's total length.
##### Multiline strings :
     The string starts with three apostrophes, not one. The same tripled apostrophe is used to terminate it.
     multiLine = '''Line #1
     Line #2'''
     print(len(multiLine))

    The snippet outputs 15.

- Count the characters carefully. Is this result correct or not? It looks okay at first glance, but when you count the characters, it doesn't.Two lines comprise 14 characters.
- The missing character is simply invisible - it's a whitespace. It's located between the two text lines. It's denoted as: \n.

- In general, strings can be:

    concatenated (joined)
    replicated.
    The first operation is performed by the + operator (note: it's not an addition) while the second by the * operator (note again: it's not a multiplication).

- The ability to use the same operator against completely different kinds of data (like numbers vs. strings) is called overloading (as such an operator is overloaded with different duties).

Analyze the example:

 - The + operator used against two or more strings produces a new string containing all the characters from its arguments (note: the order matters - this overloaded +, in contrast to its numerical version, is not commutative)
 - the * operator needs a string and a number as arguments; in this case, the order doesn't matter - you can put the number before the string, or vice versa, the result will be the same - a new string created by the nth replication of the argument's string.
###### Example :
```
str1 = 'a'
str2 = 'b'

print(str1 + str2)
print(str2 + str1)
print(5 * 'a')
print('b' * 4)
str1*= 3
print(str1)
```
Note: shortcut variants of the above operators are also applicable for strings (+= and *=).


## Operations on string :
#### ord() : 
- If you want to know a specific character's ASCII/UNICODE code point value, you can use a function named ord() (as in ordinal).
- The function needs a >strong>one-character string as its argument - breaching this requirement causes a TypeError exception, and returns a number representing the argument's code point.

#### chr() :
- If you know the code point (number) and want to get the corresponding character, you can use a function named chr().
- The function takes a code point and returns its character.

Example : 
```
print(chr(97))
print(chr(945))
print(chr(ord('x')) == 'x')
```

#### min() :
- The function finds the minimum element of the sequence passed as an argument. There is one condition - the sequence (string, list, it doesn't matter) cannot be empty, or else you'll get a ValueError exception.

Example :
print(min("aAbByYzZ"))
output : A 

Note: It's an upper-case A. Why? Recall the ASCII table - which letters occupy first locations - upper or lower?

#### max() :
- Similarly, a function named max() finds the maximum element of the sequence.

#### index() : 
- The index() method (it's a method, not a function) searches the sequence from the beginning, in order to find the first element of the value specified in its argument.
- Note: the element searched for must occur in the sequence - its absence will cause a ValueError exception.
- The method returns the index of the first occurrence of the argument (which means that the lowest possible result is 0, while the highest is the length of argument decremented by 1)

#### list() :
- The list() function takes its argument (a string) and creates a new list containing all the string's characters, one per list element.
Note: it's not strictly a string function - list() is able to create a new list from many other entities (e.g., from tuples and dictionaries).

#### count() :
- The count() method counts all occurrences of the element inside the sequence. The absence of such elements doesn't cause any problems.

#### join() :
- as its name suggests, the method performs a join - it expects one argument as a list; it must be assured that all the list's elements are strings - the method will raise a TypeError exception otherwise;
- all the list's elements will be joined into one string but...
- ...the string from which the method has been invoked is used as a separator, put among the strings;
- the newly created string is returned as a result.
```
# Demonstrating the join() method
print(",".join(["omicron", "pi", "rho"]))
```

#### swapcase() :
- The swapcase() method makes a new string by swapping the case of all letters within the source string: lower-case characters become upper-case, and vice versa.

#### title() : 
- The title() method performs a somewhat similar function - it changes every word's first letter to upper-case, turning all other ones to lower-case.


### Strings as sequences: indexing (Python's strings are sequences)
- Strings aren't lists, but you can treat them like lists in many particular cases.
 
    For example, if you want to access any of a string's characters, you can do it using indexing, just like in the example in the editor. Run the program.
- Negative indices behave as expected, too. Check this yourself.
- Iterating through the strings works, too.
- Everything you know about slices in arrays is still usable.
###### Slices example 
```
# Slices

alpha = "abdefg"

print(alpha[1:3])
print(alpha[3:])
print(alpha[:3])
print(alpha[3:-2])
print(alpha[-3:4])
print(alpha[::2])
print(alpha[1::2])

output :
bd
efg
abd
e
e
adf
beg
```

- Python's strings are immutable : This primarily means that the similarity of strings and lists is limited. Not everything you can do with a list may be done with a string.
- The first important difference doesn't allow you to use the del instruction to remove anything from a string.
- Python strings don't have the append() method - you cannot expand them in any way.

[Read String functions](https://docs.python.org/3.4/library/stdtypes.html#string-methods)