def for_loop():
    """
    ==============================
    Explanation
    ==============================
    for loop is used to iterate over a sequence (list, tuple, string, etc.)
    ==============================
    Syntax
    ==============================
    for <variable> in <sequence>:
            <statement>
            <statement>
    
            ...
    ==============================
    Example
    ==============================
    for i in [1, 2, 3, 4, 5]:
        print(i)
    ==============================
    Output
    ==============================
    1
    2
    3
    4
    5    
    """
    print(for_loop.__doc__)

def while_loop():
    """
    ==============================
    Explanation
    ==============================
    while loop is used to iterate over a sequence until a condition is met
    ==============================
    Syntax
    ==============================
    while <condition>:
            <statement>
            <statement>
            ...
    ==============================
    Example
    ==============================
    i = 0
    while i < 5:
        print(i)
        i += 1
    ==============================
    Output
    ==============================
    0
    1
    2
    3
    4
    """
    print(while_loop.__doc__)
    

def loop_with_break_else():
    """
    ==============================
    Explanation
    ==============================
    break statement is used to exit a loop prematurely
    else statement is used to execute a block of code if the loop completes normally
    ==============================
    Syntax
    ==============================
    for <variable> in <sequence>:
        <statement>
        if <condition>:
            break
    else:
        <statement>
    ==============================
    Example
    ==============================
    for i in range(10):
        if i == 5:
            break
        print(i)
    else:
        print("Loop completed normally")
    ==============================
    Output
    ==============================
    0
    1
    2
    3
    4
    Loop completed normally
    """
    print(loop_with_break_else.__doc__)
    for num in range(2, 10):
        for x in range(2, num):
            print(num, x)
            if num % x == 0:
                print(num, 'equals', x, '*', num//x)
                break
        else:
            # loop fell through without finding a factor
            print(num, 'is a prime number')



if __name__ == "__main__":
    loop_type = input("Python loops are For and while. Which loop you want to learn? Please type `for` to learn `for` and `while` to learn `while` \n")
    if loop_type == "for":
        for_loop()
    elif loop_type == "while":
        while_loop()
    else:
        print("Invalid loop type")

    loop_with_break_else()

