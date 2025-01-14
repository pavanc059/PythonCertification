# Ten animals I slam in a net

input_string = input()

isPalindrome = True
j = len(input_string)-1
i = 0
for index in range(len(input_string)//2):
    
    left_char = input_string[i]
    right_char = input_string[j]


    while left_char.isspace():
        i += 1
        left_char = input_string[i]
    
    while right_char.isspace():
        j -= 1
        right_char = input_string[j]
    if left_char.lower() != right_char.lower():
        isPalindrome = False
        print("It's not a palindrome")       
        break
    i += 1
    j -= 1
   

    
if isPalindrome:
    print("It's a palindrome")
    
