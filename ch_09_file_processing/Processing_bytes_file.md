# bytearray
Python uses specialized classes to store amorphous data. Amorphous data is data which have no specific shape or form - they are just a series of bytes.
- This doesn't mean that these bytes cannot have their own meaning, or cannot represent any useful object, e.g., bitmap graphics.
- Amorphous data cannot be stored using any of the previously presented means - they are neither strings nor lists.
- Python has more than one such container - one of them is a specialized class name `bytearray` - as the name suggests, it's an array containing (amorphous) bytes.
- If you want to have such a container, e.g., in order to read in a bitmap image and process it in any way, you need to create it explicitly, using one of available constructors.

`data = bytearray(10)` - This invocation creates a bytearray object able to store ten bytes. `Note: such a constructor fills the whole array with zeros.`
- Bytearrays resemble lists in many respects. For example, they are mutable, they're a subject of the len() function, and you can access any of their elements using conventional indexing.
- There is one important limitation - you mustn't set any byte array elements with a value which is not an integer (violating this rule will cause a TypeError exception) and you're not allowed to assign a value that doesn't come from the range 0 to 255 inclusive (unless you want to provoke a ValueError exception).
```Python
data = bytearray(10)

for i in range(len(data)):
    data[i] = 10 - i

for b in data:
    print(hex(b))
```

```Python
from os import strerror

data = bytearray(10)

for i in range(len(data)):
    data[i] = 10 + i

try:
    bf = open('file.bin', 'wb')
    bf.write(data)
    bf.close()
except IOError as e:
    print("I/O error occurred:", strerr(e.errno))
```
- First, we initialize bytearray with subsequent values starting from 10; if you want the file's contents to be clearly readable, replace 10 with something like ord('a') - this will produce bytes containing values corresponding to the alphabetical part of the ASCII code (don't think it will make the file a text file - it's still binary, as it was created with a wb flag);
- Then, we create the file using the open() function - the only difference compared to the previous variants is the open mode containing the b flag;
- The write() method takes its argument (bytearray) and sends it (as a whole) to the file;
- The stream is then closed in a routine way.


##### read bytes from a stream
An alternative way of reading the contents of a binary file is offered by the method named `read()`
- Invoked without arguments, it tries to read all the contents of the file into the memory, making them a part of a newly created object of the bytes class.
- This class has some similarities to bytearray, with the exception of one significant difference - it's immutable.

```python
from os import strerror

try:
    bf = open('file.bin', 'rb')
    data = bytearray(bf.read())
    bf.close()

    for b in data:
        print(hex(b), end=' ')

except IOError as e:
    print("I/O error occurred:", strerr(e.errno))
```
- If the read() method is invoked with an argument, it specifies the maximum number of bytes to be read.
- The method tries to read the desired number of bytes from the file, and the length of the returned object can be used to determine the number of bytes actually read.