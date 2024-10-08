""" This utility functions are built based on python version 3.8.10 and referenced from https://docs.python.org/


"""
import string



#This function returns true if given string is ASCII takes string as first arguments and seecond argument as boolean(True=upper/False=lower) to find in ascii upper values or lower
def findGivenStringisASCII(inputString :str,  lower :bool) -> bool:    
    if(inputString and isinstance(inputString, str)):
        if(lower):
            for inputString in string.ascii_uppercase:
                return True
        elif(not lower):
            for inputString in string.ascii_lowercase:
                    return True
        else:
            for x in inputString:
                if (x not in string.ascii_letters):
                    return False
            return True
    else:
        return "Input passed to the function is not string evaluated by isinstance or an empty strinf passed"
    
def isDigit_Hexa_Octa(input, startPosition=0, endPosition=0, isDigit=False, isHexa=False, isOcta=False):
    listOfResults = []
    if(startPosition==0 and endPosition==0):
        length = range(len(input))
    elif(startPosition!=0 and endPosition==0):
        length =  range(startPosition, len(input))
    elif(startPosition!=0 and endPosition!=0):
        length = range(startPosition, endPosition)   
    
    for a in length:
        if(isDigit == True and (input[a] in string.digits)):
           listOfResults.append(True)
        elif(isHexa == True and (input[a] in string.hexdigits)):
            listOfResults.append(True)
        elif(isOcta == True and (input[a] in string.octdigits)):
            listOfResults.append(True)
        else:
            listOfResults.append(False)
            
    if((len(listOfResults))<=1):
        return listOfResults[0]
    else:
        return listOfResults
        

#print(isDigit_Hexa_Octa("A", isHexa=True))
