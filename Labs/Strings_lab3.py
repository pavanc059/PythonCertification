input_string = input()
shifts = int(input())
output_string = ""

if shifts > 25:
    print("Shifts must be less than or equal 25")
    exit()

for char in input_string:
    if char == " ":
        output_string += char
    else:
        if ord(char) >= 65 and ord(char) <= 90:
            if ord(char) + shifts > 90:
                output_string += chr(ord(char) - 26 + shifts)
            else:
                output_string += chr(ord(char) + shifts)
        elif ord(char) >= 97 and ord(char) <= 122:
            if ord(char) + shifts > 122:
                output_string += chr(ord(char) - 26 + shifts)
            else:
                output_string += chr(ord(char) + shifts)
        else:
            output_string += char           
        
    
print(output_string)


