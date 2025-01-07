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


