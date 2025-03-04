# Generators
A Python generator is a piece of specialized code able to produce a series of values, and to control the iteration process. This is why generators are very often called iterators, and although some may find a very subtle distinction between these two, we'll treat them as one.

- The range() function is, in fact, a generator, which is (in fact, again) an iterator.
- A function returns one, well-defined value - it may be the result of a more or less complex evaluation of, e.g., a polynomial, and is invoked once - only once.
- A generator returns a series of values, and in general, is (implicitly) invoked more than once. Ex : the range() generator is invoked six times, providing five subsequent values from zero to four, and finally signaling that the series is complete.

#### Creating custom generator class

The iterator protocol is a way in which an object should behave to conform to the rules imposed by the context of the `for` and `in` statements. An object conforming to the iterator protocol is called an iterator.

An iterator must provide two methods:
- `__iter__()` which should return the object itself and which is invoked once (it's needed for Python to successfully start the iteration)
- `__next__()` which is intended to return the next value (first, second, and so on) of the desired series - it will be invoked by the for/in statements in order to pass through the next iteration; if there are no more values to provide, the method should raise the StopIteration exception.

```python linenums="1"
class Fib:
	def __init__(self, nn):
		print("__init__")
		self.__n = nn
		self.__i = 0
		self.__p1 = self.__p2 = 1

	def __iter__(self):
		print("__iter__")		
		return self

	def __next__(self):
		print("__next__")				
		self.__i += 1
		if self.__i > self.__n:
			raise StopIteration
		if self.__i in [1, 2]:
			return 1
		ret = self.__p1 + self.__p2
		self.__p1, self.__p2 = self.__p2, ret
		return ret

for i in Fib(10):
	print(i)

# Output : 
__init__
__iter__
__next__
1
__next__
1
__next__
2
__next__
3
__next__
5
__next__
8
__next__
13
__next__
21
__next__
34
__next__
55
__next__

```
the Fibonacci numbers (Fibi) are defined as follows:

Fib1 = 1
Fib2 = 1
Fibi = Fibi-1 + Fibi-2

- The first two Fibonacci numbers are equal to 1;
- Any other Fibonacci number is the sum of the two previous ones (e.g., Fib3 = 2, Fib4 = 3, Fib5 = 5, and so on)
- lines 2 through 6: the class constructor prints a message (we'll use this to trace the class's behavior), prepares some variables (__n to store the series limit, __i to track the current Fibonacci number to provide, and __p1 along with __p2 to save the two previous numbers);
- ines 8 through 10: the `__iter__` method is obliged to return the iterator object itself; its purpose may be a bit ambiguous here, but there's no mystery; try to imagine an object which is not an iterator (e.g., it's a collection of some entities), but one of its components is an iterator able to scan the collection; the `__iter__` method should extract the iterator and entrust it with the execution of the iteration protocol; as you can see, the method starts its action by printing a message;
- lines 12 through 21: the `__next__` method is responsible for creating the sequence; it's somewhat wordy, but this should make it more readable; first, it prints a message, then it updates the number of desired values, and if it reaches the end of the sequence, the method breaks the iteration by raising the StopIteration exception; the rest of the code is simple, and it precisely reflects the definition we showed you earlier;
- lines 23 and 24 make use of the iterator.
- the iterator object is instantiated first;
- next, Python invokes the __iter__ method to get access to the actual iterator;
- the __next__ method is invoked eleven times - the first ten times produce useful values, while the eleventh terminates the iteration.


```python
class Fib:
	def __init__(self, nn):
		self.__n = nn
		self.__i = 0
		self.__p1 = self.__p2 = 1

	def __iter__(self):
		print("Fib iter")
		return self

	def __next__(self):
		self.__i += 1
		if self.__i > self.__n:
			raise StopIteration
		if self.__i in [1, 2]:
			return 1
		ret = self.__p1 + self.__p2
		self.__p1, self.__p2 = self.__p2, ret
		return ret

class Class:
	def __init__(self, n):
		self.__iter = Fib(n)

	def __iter__(self):
		print("Class iter")
		return self.__iter;

object = Class(8)

for i in object:
	print(i)
```

- The object of the class may be used as an iterator when (and only when) it positively answers to the `__iter__` invocation - this class can do it, and if it's invoked in this way, it provides an object able to obey the iteration protocol.

#### yield keyword
- The iterator protocol isn't particularly difficult to understand and use, but it is also indisputable that the protocol is rather inconvenient.The main discomfort it brings is the need to save the state of the iteration between subsequent `__iter__` invocations.
- This is why Python offers a much more effective, convenient, and elegant way of writing iterators.The concept is fundamentally based on a very specific and powerful mechanism provided by the `yield` keyword.

```python
def fun(n):
    for i in range(n):
        return i

#for loop has no chance to finish its first execution, as the return will break it irrevocably.	
# repalcing return with yeild made this function as generator
def fun(n):
    for i in range(n):
        yield i
```
- We've added yield instead of return. This little amendment turns the function into a generator, and executing the yield statement has some very interesting effects.
- First of all, it provides the value of the expression specified after the yield keyword, just like return, but doesn't lose the state of the function.
- All the variables' values are frozen, and wait for the next invocation, when the execution is resumed (not taken from scratch, like after return).
- There is one important limitation: such a function should not be invoked explicitly as - in fact - it isn't a function anymore; it's a generator object. The invocation will return the object's identifier, not the series we expect from the generator.

#### Building a generator
```python
def fun(n):
    for i in range(n):
        yield i

for v in fun(5):
    print(v)

```
What if you need a generator to produce the first n powers of 2?
```python
def powersOf2(n):
    pow = 1
    for i in range(n):
        yield pow
        pow *= 2

for v in powersOf2(8):
    print(v)

t = [x for x in powersOf2(5)]
```
- Use yeild to store state vairables like pow in above example
- Generators may also be used within list comprehensions. `t = [x for x in powersOf2(5)]` 
- The list() function can transform a series of subsequent generator invocations into a real list. `t = list(powersOf2(3))`
- list comprehension - a simple and very impressive way of creating lists and their contents.
```python
listOne = []

for ex in range(6):
    listOne.append(10 ** ex)


listTwo = [10 ** ex for ex in range(6)]

print(listOne)
print(listTwo)

#conditional expression
lst = []

for x in range(10):
    lst.append(1 if x % 2 == 0 else 0)

print(lst)

```
- conditional expression - a way of selecting one of two different values based on the result of a Boolean expression.
```python
lst = [1 if x % 2 == 0 else 0 for x in range(10)]
```
- Just one change can turn any comprehension into a generator. The brackets make a comprehension, the parentheses make a generator.
```python
lst = [1 if x % 2 == 0 else 0 for x in range(10)] # list 
genr = (1 if x % 2 == 0 else 0 for x in range(10)) # generator

for v in lst:
    print(v, end=" ")
print()

for v in genr:
    print(v, end=" ")
print()
```
- Note: the same appearance of the output doesn't mean that both loops work in the same way. In the first loop, the list is created (and iterated through) as a whole - it actually exists when the loop is being executed.
- In the second loop, there is no list at all - there are only subsequent values produced by the generator, one by one.

### Get in details 
[PEP 0789](https://peps.python.org/pep-0789/)