## Processing text files
Reading a text file's contents can be performed using several different methods.

- The most basic of these methods is the one offered by the `read()` function, which you were able to see in action in the previous lesson.
- If applied to a text file, the function is able to:
  1)  read a desired number of characters (including just one) from the file, and return them as a string;
  2)  read all the file contents, and return them as a string;
  3)  if there is nothing more to read (the virtual reading head reaches the end of the file), the function returns an empty string.
   
Simplest variant and use a file named text.txt. The file has the following contents:
``` 
Beautiful is better than ugly.
Explicit is better than implicit.
Simple is better than complex.
Complex is better than complicated. 
```
```python
from os import strerror

try:
    cnt = 0
    s = open('text.txt', "rt")
    ch = s.read(1)
    while ch != '':
        print(ch, end='')
        cnt += 1
        ch = s.read(1)
    s.close()
    print("\n\nCharacters in file:", cnt)
except IOError as e:
    print("I/O error occurred: ", strerr(e.errno))
```


- use the try-except mechanism and open the file of the predetermined name (text.txt in our case)
- try to read the very first character from the file (ch = s.read(1))
- if you succeed (this is proven by a positive result of the while condition check), output the character (note the end= argument - it's important! You don't want to skip to a new line after every character!);
- update the counter (cnt), too;
- try to read the next character, and the process repeats.

##### read(int numberOfchar) method
The  `read()` method reads file content. The read() function, invoked without any arguments or with an argument that evaluates to None will read whole file into memory

`Remember - reading a terabyte-long file using this method may corrupt your OS.`

##### readline() method
- If you want to treat the file's contents as a set of lines, not a bunch of characters, the readline() method will help you with that.
- The method tries to read a complete line of text from the file, and returns it as a string in the case of success. Otherwise, it returns an empty string.

##### readlines() method
- The readlines() method, when invoked without arguments, tries to read all the file contents, and returns a list of strings, one element per file line.
- If you're not sure if the file size is small enough and don't want to test the OS, you can convince the readlines() method to read not more than a specified number of bytes at once (the returning value remains the same - it's a list of a string).
- The maximum accepted input buffer size is passed to the method as its argument.
`Note: when there is nothing to read from the file, the method returns an empty list. Use it to detect the end of the file.`
- You may expect that readlines() can process a file's contents more effectively than readline(), as it may need to be invoked fewer times.
- with parameter int will read number of lines based on character fit 
example :
file content :
Beautiful is better than ugly.
Explicit is better than implicit.
Simple is better than complex.
Complex is better than complicated.

readlines(40)

will read first and second line 
output : 
['Beautiful is better than ugly.\n', 'Explicit is better than implicit.\n']

readlines(30)
output : ['Beautiful is better than ugly.\n']

`the object returned by the open() function in text mode is an instance of the iterable class. The iteration protocol defined for the file object is very simple - its __next__ method just returns the next line read in from the file. You can expect that the object automatically invokes close() when any of the file reads reaches the end of the file.`

```python
from os import strerror

try:
	ccnt = lcnt = 0
	for line in open('text.txt', 'rt'):
		lcnt += 1
		for ch in line:
			print(ch, end='')
			ccnt += 1
	print("\n\nCharacters in file:", ccnt)
	print("Lines in file:     ", lcnt)
except IOError as e:
	print("I/O error occurred: ", strerr(e.errno))
```

##### write()
- Writing text files seems to be simpler, as in fact there is one method that can be used to perform such a task.
- The method is named write() and it expects just one argument - a string that will be transferred to an open file (don't forget - the open mode should reflect the way in which the data is transferred - writing a file opened in read mode won't succeed).
- No newline character is added to the write()'s argument, so you have to add it yourself if you want the file to be filled with a number of lines.
`Note: you can use the same method to write to the stderr stream, but don't try to open it, as it's always open implicitly.`
- For example, if you want to send a message string to stderr to distinguish it from normal program output, it may look like this:
```python
import sys
sys.stderr.write("Error message")
```