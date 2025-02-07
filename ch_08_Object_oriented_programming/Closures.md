# Closures
In Python, a closure is typically a function defined inside another function. This inner function grabs the objects defined in its enclosing scope and associates them with the inner function object itself. The resulting combination is called a closure.
- closure is a technique which allows the storing of values in spite of the fact that the context in which they have been created does not exist anymore.
```python
def outer(par):
    loc = par

var = 1
outer(var)

print(par)
print(loc)
```
- The last two lines will cause a NameError exception - neither par nor loc is accessible outside the function. Both the variables exist when and only when the outer() function is being executed.
```python
#closure function
def outer(par):
	loc = par
	def inner():
		return loc
	return inner

var = 1
fun = outer(var)
print(fun())

```
- The inner() function returns the value of the variable accessible inside its scope, as inner() can use any of the entities at the disposal of outer()
- The outer() function returns the inner() function itself; more precisely, it returns a copy of the inner() function, the one which was frozen at the moment of outer()'s invocation; the frozen Function contains its full environment, including the state of all local variables, which also means that the value of loc is successfully retained, although outer() ceased to exist a long time ago.
- A closure has to be invoked in exactly the same way in which it has been declared.
- It is fully possible to declare a closure equipped with an arbitrary number of parameters
- This means that the closure not only makes use of the frozen environment, but it can also modify its behavior by using values taken from the outside.
-  you can create as many closures as you want using one and the same piece of code. like makeclosure sample below
```python
def makeclosure(par):
	loc = par
	def power(p):
		return p ** loc
	return power

fsqr = makeclosure(2)
fcub = makeclosure(3)
for i in range(5):
	print(i, fsqr(i), fcub(i))
```
