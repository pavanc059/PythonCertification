import timeit

def mysplit(stringInput):
    start = 0
    stringList = []
    if stringInput.isspace():
        return stringList
    for i, value in enumerate(stringInput):
        if value == " ":
            stringList.append(stringInput[start:i])
            start = i + 1
        
        if i == (len(stringInput)-1):
            stringList.append(stringInput[start:i+1])
    return stringList

def mysplit2(stringInput):
    start = 0
    control = True
    index = 0
    stringList = []
    if stringInput.isspace():
        return stringList
    while control:
        if index == len(stringInput)-1:
            stringList.append(stringInput[start:index+1])
            control = False

        if stringInput[index] == " ":
            stringList.append(stringInput[start:index])
            start = index + 1
        
        index += 1
    return stringList
        

inputValue = input("Enter a string: ")
time1 = timeit.timeit(lambda: mysplit(inputValue), number=1000)
print(f"mysplit average execution time over 1000 runs: {time1/1000:.6f} seconds")

# Time the second function
time2 = timeit.timeit(lambda: mysplit2(inputValue), number=1000)
print(f"mysplit2 average execution time over 1000 runs: {time2/1000:.6f} seconds")       
  


#inputValue = input("Enter a string: ")

#print(mysplit2(inputValue))