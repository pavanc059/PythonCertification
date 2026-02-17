### Packages in Python

- Multiple module .py files can be packaged into single python packages without `__init__.py` file you need to import packages using packageName.module. 
- `__init__.py` file can be used to define global variables also when you import package it executes `__init__.py` file.
- In `__init__.py` if you include "`__all__ = ['mod1', 'mod2']`" then when you import everythign from pakage all the mudules specified inside `__all__` list will be imported with statement from pkg import *. You can also limit the methods and variables to be imported with '*' by specifying `__all__` list in actual module mod1 or mod2