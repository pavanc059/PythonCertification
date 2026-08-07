# Functional Programming in Python

## Overview
Functional programming is a programming paradigm that treats computation as the evaluation of mathematical functions, emphasizing immutability and avoiding changing state.

## Key Concepts

### Pure Functions
Functions that always produce the same output for the same input and have no side effects.

```python
# Pure function
def add(a, b):
    return a + b
```

### Immutability
Data should not be modified after creation; instead, create new data structures.

```python
# Use tuples instead of lists
coordinates = (10, 20)
```

### First-Class Functions
Functions are treated as values and can be passed as arguments.

```python
def apply_operation(func, a, b):
    return func(a, b)

result = apply_operation(add, 5, 3)
```

## Built-in Functional Tools

### `map()`
Applies a function to every item in an iterable.

```python
numbers = [1, 2, 3, 4]
squared = list(map(lambda x: x**2, numbers))
```

### `filter()`
Filters items based on a predicate function.

```python
numbers = [1, 2, 3, 4, 5]
evens = list(filter(lambda x: x % 2 == 0, numbers))
```

### `reduce()`
Applies a function cumulatively to items in an iterable.

```python
from functools import reduce
numbers = [1, 2, 3, 4]
product = reduce(lambda x, y: x * y, numbers)
```

### Lambda Functions
Anonymous functions for simple operations.

```python
double = lambda x: x * 2
```

## Higher-Order Functions
Functions that accept or return other functions.
