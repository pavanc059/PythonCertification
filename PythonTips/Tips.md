1) By default Python uses UTF-8 encoding to change default encoding you need to insert below comment line with encoding scheem 
  # -*- coding: encoding -*
  #!/usr/bin/env python3 (shebang)
  # -*- coding: cp1252 -*-

2) Division in python always return float type to return int and discard any float value use "//"
to calculate reminder use "%" ex : 5%2 = 1
   

3) To do power calculation use "**" ex: 2^4 --> 2**4 = 16
4) In interactive mode last printed expression is assigned to "_" 
5) Python keywords : ['False', 'None', 'True', 'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield']
6) print function concatenation if you want to print string and integer using print function like print("String" + integer) this would throw and error because we're adding string with integer you need to parse one of the value to make it work as below 
        - print("String" + str(integer)) or you can pass multiple parameters to print function  as print("String", integer)
7) In python 2 == 2. (True)
8) Operator priority table
 
        Priority  |	Operator               |
        --------  | ---------------------- | --------------
           1 	    |   +, -, ~ 	           |    unary
           2 	    |   ** 	                 |    
           3 	    |   *, /, //, % 	       |
           4 	    |   +, - 	               |    binary
           5      |  <<, >>                |
           6 	    |   <, <=, >, >= 	       |
           7 	    |   ==, !=               |
           8      |    &                   |
           9      |     |                  |
           10     |  =, +=, -=, *=, /=, %=,| 
                  |  &=, ^=, |=, >>=, <<=  | 
9) Variable assignment in python can also be done as following ways
    1) x = y = z = 5
    2) x, y, z = 5, 10, 20
   
10) while loop in python can have else condition which executes when you while condition body don't execute 
    [syntax] : while condition:
                    #while_body
               else:
                    #else_condition body
    
11) else in for loop executes at the end of for execution 
    [syntax] : for variable in range(value):
                    #for_body
               else:
                    #else block the executes at end of for loop
12) logical operators and bit wise operators in python. logical operators operate on final value of the expression but bit wise operators work on each bit as example below
    [Example] : i = 15; j = 22
                print(i and j) : 22
                print(i & j)   : 6
                print(j and i) : 15
                print(j & i)   : 6    
13) list in python can store list of value of different types as shown below
        numbers = [10, [2,4,6], 7, 2.0, 'test']
