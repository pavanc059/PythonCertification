# Python Operators

### Arithmetic operators :

`**` - exponentiation (**2^3**)

example : 2 ** 3 = 8, 2 ** 3. = 8.0, 2.** 3 = 8.0,

'*' - multiplication

'/' - division

'//' - integer division (removes floating point of division operation ex : 9//5 = 1 and 9/5 = 1.8)

'%' - remainder (modulo) ex: 4%2 = 0, 4%3=1

'+' - addition

'-' - subtraction

### Unary operator :

'+ and -' Unary operator (Ex : -2 and +5)

### Operator priorities:

upper group has higher precedence than the lower ones

| Operators                                                                   | Meaning                                           |
| --------------------------------------------------------------------------- | ------------------------------------------------- |
| `()`                                                                      | Parentheses                                       |
| `**`                                                                      | Exponent                                          |
| `+x`,`-x`,`~x`                                                        | Unary plus, Unary minus, Bitwise NOT              |
| `*`,`/`,`//`,`%`                                                    | Multiplication, Division, Floor division, Modulus |
| `+`,`-`                                                                 | Addition, Subtraction                             |
| `<<`,`>>`                                                               | Bitwise shift operators                           |
| `&`                                                                       | Bitwise AND                                       |
| `^`                                                                       | Bitwise XOR                                       |
| `\|`                                                                       | Bitwise OR                                        |
| `==`,`!=`,`>`,`>=`,`<`,`<=`,`is`,`is not`,`in`,`not in` | Comparisons, Identity, Membership operators       |
| `not`                                                                     | Logical NOT                                       |
| `and`                                                                     | Logical AND                                       |
| `or`                                                                      | Logical OR                                        |

> Operators bindings : Most of Python's operators have left-sided binding, which means that the calculation of the expression is conducted from left to right. Except **the exponentiation operator uses right-sided binding** .



### Shortcut operators : `variable = variable 'operator' expression` as `variable '`operator '`= expression`

ex : `i = i + 2 * j`   ⇒   `i += 2 * j`
