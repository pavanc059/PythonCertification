class Stack:
    def __init__(self):
        self.__stackList = []

    def push(self, element):
        self.__stackList.append(element)

    def pop(self):
        val = self.__stackList[-1]
        del self.__stackList[-1]
        return val

class AddingStack(Stack):
    def __init__(self):
        Stack.__init__(self)
        self.__sum = 0

    def push(self, element):
        self.__sum += element
        Stack.push(self, element)

    def pop(self):
        val = Stack.pop(self)
        self.__sum -= val
        return val
    
    def getSum(self):
        return self.__sum
        


stackObject = AddingStack()

for i in range(5):
    stackObject.push(i)
print(stackObject.getSum())

for i in range(5):
    print(stackObject.pop())