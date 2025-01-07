def readint(prompt, min, max):   
    input_val = input(prompt)
    try:
        input_val = int(input_val)
        ok = True
    except:
        raise Exception("wrong input")
    
    if input_val < min or input_val > max:
        raise Exception("the value is not within permitted range (-10..10)")    
    
    return input_val

ok = False
while not ok:
    try:
        v = readint("Enter a number from -10 to 10: ", -10, 10)
        print("The number is:", v)
        ok = True
    except Exception as e:
        print('Error:',e)

    