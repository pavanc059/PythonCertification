dateOfBirth = input("Enter your date of birth in yyyymmdd ")


one_digit = ""

while len(dateOfBirth) > 1:
    sum = 0
    for digit in dateOfBirth:
        sum+=int(digit)
    
    dateOfBirth = str(sum)

print(dateOfBirth)

    


