# The lambda function
- The `lambda` function is a concept borrowed from mathematics, more specifically, from a part called the `Lambda` calculus, but these two phenomena are not the same.

- Mathematicians use the `Lambda` calculus in many formal systems connected with logic, recursion, or theorem provability. Programmers use the `lambda` function to simplify the code, to make it clearer and easier to understand.

- A `lambda` function is a function without a name (you can also call it an anonymous function). Of course, such a statement immediately raises the question: how do you use anything that cannot be identified?

- Fortunately, it's not a problem, as you can name such a function if you really need, but, in fact, in many cases the `lambda` function can exist and work while remaining fully incognito.

- The declaration of the `lambda` function doesn't resemble a normal function declaration in any way.

syntax :
`lambda parameters : expression`

```python
two = lambda : 2
sqr = lambda x : x * x
pwr = lambda x, y : x ** y

for a in range(-2, 3):
    print(sqr(a), end=" ")
    print(pwr(a, two()))

Output :
4 4
1 1
0 0
1 1
4 4
```
- The first lambda is an anonymous parameterless function that always returns 2. As we've assigned it to a variable named two, we can say that the function is not anonymous anymore, and we can use the name to invoke it.
- The second one is a one-parameter anonymous function that returns the value of its squared argument. We've named it as such, too.
- The third lambda takes two parameters and returns the value of the first one raised to the power of the second one. The name of the variable which carries the lambda speaks for itself. We don't use pow to avoid confusion with the built-in function of the same name and the same purpose.
- lambda is powerful when we use as anonymous parts of code intended to evaluate a result.
- Imagine that we need a function (we'll name it printfunction) which prints the values of a given (other) function for a set of selected arguments.
- We want printfunction to be universal - it should accept a set of arguments put in a list and a function to be evaluated, both as arguments - we don't want to hardcode anything.
```python
def printfunction(args, fun):
	for x in args:
		print('f(', x,')=', fun(x), sep='')

def poly(x):
	return 2 * x**2 - 4 * x + 2

printfunction([x for x in range(-2, 3)], poly)

Output:
f(-2)=18
f(-1)=8
f(0)=2
f(1)=0
f(2)=2
```
- The first, a list of arguments for which we want to print the results;
- The second, a function which should be invoked as many times as the number of values that are collected inside the first parameter.
`Note: we've also defined a function named poly() - this is the function whose values we're going to print. The calculation the function performs isn't very sophisticated - it's the polynomial (hence its name) of a form: f(x) = 2x2 - 4x + 2`
- The name of the function is then passed to the printfunction() along with a set of five different arguments - the set is built with a list comprehension clause.
- Can we avoid defining the poly() function using lambda as below
```python
def printfunction(args, fun):
	for x in args:
		print('f(', x,')=', fun(x), sep='')

printfunction([x for x in range(-2, 3)], lambda x: 2 * x**2 - 4 * x + 2)
```
- The `printfunction()` has remained exactly the same, but there is no `poly()` function. We don't need it anymore, as the polynomial is now directly inside the `printfunction()` invocation in the form of a lambda defined in the following way: `lambda x: 2 * x**2 - 4 * x + 2`.

## map() function
The map() function takes two arguments:
- A function;
- a list. (the second map() argument may be any entity that can be iterated (e.g., a tuple, or just a generator))
`map(function, list)`
- `map()` can accept more than two arguments.
- The `map()` function applies the function passed by its first argument to all its second argument's elements, and returns an iterator delivering all subsequent function results. You can use the resulting iterator in a loop, or convert it into a list using the `list()` function.
```python
list1 = [x for x in range(5)]
list2 = list(map(lambda x: 2 ** x, list1))
print(list2)
for x in map(lambda x: x * x, list2):
	print(x, end=' ')
print()

Output:
[1, 2, 4, 8, 16]
1 4 16 64 256
```
- build the list1 with values from 0 to 4;
- next, use map along with the first lambda to create a new list in which all elements have been evaluated as 2 raised to the power taken from the corresponding element from list1;
- list2 is printed then;
- In the next step, use the map() function again to make use of the generator it returns and to directly print all the values it delivers; as you can see, we've engaged the second lambda here - - It just squares each element from list2.

## filter() function
It expects the same kind of arguments as map(), but does something different - it filters its second argument while being guided by directions flowing from the function specified as the first argument (the function is invoked for each list element, just like in map()).

- The elements which return True from the function pass the filter - the others are rejected.
```python
from random import seed, randint

seed()
data = [ randint(-10,10) for x in range(5) ]
filtered = list(filter(lambda x: x > 0 and x % 2 == 0, data))
print(data)
print(filtered)
```
Note: we've made use of the random module to initialize the random number generator (not to be confused with the generators we've just talked about) with the seed() function, and to produce five random integer values from -10 to 10 using the randint() function.


### Get in detail
[PEP 0312](https://peps.python.org/pep-0312/)