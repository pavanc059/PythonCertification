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
