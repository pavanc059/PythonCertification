## Extended function argument
Function arguments, we should recall the following facts:
- some functions can be invoked without arguments;
- functions may require a specific number of arguments with no exclusions; we have to pass a required number of arguments in an imposed order to follow function definition;
- functions might have already defined default values for some parameters, so we do not have to pass all arguments as missing arguments, complete with defaults; parameters with default values are presented as keyword parameters;
- we can pass arguments in any order if we are assigning keywords to all argument values, otherwise positional ones are the first ones on the arguments list.

`print()` function:
```python
print()
print(3)
print(1, 20, 10)
print('--', '++')
```
All presented invocations of the print() function end correctly, and the argument values are passed to the standard output. 

### *args and **kwargs
These two special identifiers (named *args and **kwargs) should be put as the last two parameters in a function definition. Their names could be changed because it is just a convention to name them 'args' and 'kwargs', but it’s more important to sustain the order of the parameters and leading asterisks.

- `*args` – refers to a tuple of all additional, not explicitly expected positional arguments, so arguments passed without keywords and passed next after the expected arguments. In other words, *args collects all unmatched positional arguments;
- `**kwargs (keyword arguments)` – refers to a dictionary of all unexpected arguments that were passed in the form of keyword=value pairs. Likewise, **kwargs collects all unmatched keyword arguments.
  
In Python, asterisks are used to denote that args and kwargs parameters are not ordinary parameters and should be unpacked, as they carry multiple items.

### how to combine *args, a key word, and **kwargs in one definition
```python
def combiner(a, b, *args, c=20, **kwargs):
    super_combiner(c, *args, **kwargs)
def super_combiner(my_c, *my_args, **my_kwargs):
    print('my_args:', my_args)
    print('my_c:', my_c)
    print('my_kwargs', my_kwargs)
combiner(1, '1', 1, 1, c=2, argument1=1, argument2='1')
```