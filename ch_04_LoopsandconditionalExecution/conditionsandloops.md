* if-else statement: more conditional execution
* Nested if-else statements :First, consider the case where the instruction placed after the if is another if
* elif statement : elif is used to check more than just one condition, and to stop when the first statement which is true is found.

  * you  **mustn't use `else` without a preceding `if`** ;
  * `else` is always the  **last branch of the cascade** , regardless of whether you've used `elif` or not;
  * `else` is an **optional** part of the cascade, and may be omitted;
  * if there is an else branch in the cascade, only one of all the branches is executed;
  * if there is no else branch, it's possible that none of the available branches is executed.

  ### Loops :

  | Loop Type          | syntax                                                                                                                             | sample                           |
  | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
  | while              | while conditional_expression:<br />    instruction<br />while repeats the execution as long as the condition evaluates to True. | <br />`# 0 terminates execution. |
  | while number != 0: |                                                                                                                                    |                                  |

  # Check if the number is odd.

  if number % 2 == 1:

  # Increase the odd_numbers counter.

  odd_numbers += 1
  else:

  # Increase the even_numbers counter.

  even_numbers += 1

  # Read the next number.

  number = int(input("Enter a number or type 0 to stop: "))``<br /><br />` |

##### For Loop :

| Loop Type                                | syntax                                                                 | sample               |
| ---------------------------------------- | ---------------------------------------------------------------------- | -------------------- |
| for                                      | for control_variable in list/range(values):<br />     #do_something | `for i in range(10): |
| print("The value of i is currently", i)` |                                                                        |                      |

Understanding above sample :

* the *for* keyword opens the `for` loop; note -
  there's no condition after it; you don't have to think about conditions,
  as they're checked internally, without any intervention;
* any variable after the *for* keyword is the **control variable** of the loop; it counts the loop's turns, and does it automatically;
* the *in* keyword introduces a syntax element describing the range of possible values being assigned to the control variable;
* the `range()` function (this is a very special function)
  is responsible for generating all the desired values of the control
  variable; in our example, the function will create (we can even say that
  it will **feed** the loop with) subsequent values from the following set: 0, 1, 2 .. 97, 98, 99; note: in this case, the `range()` function starts its job from 0 and finishes it one step (one integer number) before the value of its argument;
* The loop has been executed ten times (it's the `range()` function's argument)
* The `range()` function invocation may be equipped with two arguments, not just one.
* The first argument determines the initial (first) value of the control variable amd second/last argument is max value +1 that control variable should reach
* Example : for i in range(2, 8):    first value for i is 2 and last value of i is 7 not 8

Loop Control statements :

* **Break:** A break statement in Python alters the flow of a loop by terminating it once a specified condition is met.
* **Continue:** The continue statement in Python is used to skip the remaining code inside a loop for the current iteration only.
* **Pass:**  The pass statement in Python is used when a statement or a condition is required to be present in the program, but we don’t want any command or code to execute. It’s typically used as a placeholder for future code.

##### Additional Info :

* Both "for" and "while" loop has a branch "else" The loop's else branch is always executed once, regardless of whether the loop has entered its body or not.
  Exmaple :
  ```
  i = 1
  while i < 5:
      print(i)
      i += 1
  else:
      print("else:", i)
  ```

##### Match statement :
* A match statement takes an expression and compares its value to successive patterns given as one or more case blocks. This is superficially similar to a switch statement in C, Java or JavaScript (and many other languages).
* Only the first pattern that matches gets executed and it can also extract components (sequence elements or object attributes) from the value into variables.
```
def http_error(status):
    match status:
        case 400:
            return "Bad request"
        case 404:
            return "Not found"
        case 418:
            return "I'm a teapot"
        case _:
            return "Something's wrong with the internet"

Match Python object 

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

def where_is(point):
    match point:
        case Point(x=0, y=0):
            print("Origin")
        case Point(x=0, y=y):
            print(f"Y={y}")  
            print(type(point) is Point)      
        case Point(x=x, y=0):
            print(f"X={x}")
        case Point(x=x, y=y):
            print(f"X={x} | Y={y}")        
        case Point():
            print("Somewhere else")
        case _:
            print("Not a point")

match args is used to match arguments to match case object 
class Point:
    __match_args__ = (x,y)
    def __init__(self, x, y):
        self.x = x
        self.y = y

def where_is(point):
    match point:
        case Point(0, 0):
            print("Origin")
        case Point(0, y):
            print(f"Y={y}")  
            print(type(point) is Point)      
        case Point(x, 0):
            print(f"X={x}")
        case Point(x, y):
            print(f"X={x} | Y={y}")        
        case Point():
            print("Somewhere else")
        case _:
            print("Not a point")

```
In practical terms, this allows for more concise pattern matching syntax. For example, if you have a class like this:
```
class Point:
    __match_args__ = ('x', 'y')
    def __init__(self, x, y):
        self.x = x
        self.y = y

```
You can now use a more compact syntax in a match statement:
```
def describe_point(point):
    match point:
        case Point(0, 0):
            return "Origin"
        case Point(0, y):
            return f"On the Y-axis at {y}"
        case Point(x, 0):
            return f"On the X-axis at {x}"
        case Point(x, y):
            return f"At coordinates ({x}, 
```
Without __match_args__, you'd have to use a more verbose syntax:
```
case Point(x=0, y=0):
    # ...
```