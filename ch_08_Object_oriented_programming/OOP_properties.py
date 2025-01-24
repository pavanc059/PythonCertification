class ExampleClass:
    def __init__(self, val = 1):
        self.first = val

    def setSecond(self, val):
        self.second = val


exampleObject1 = ExampleClass()
exampleObject2 = ExampleClass(2)

exampleObject2.setSecond(3)

exampleObject3 = ExampleClass(4)
exampleObject3.third = 5


print(exampleObject1.__dict__)
print(exampleObject2.__dict__)
print(exampleObject3.__dict__)