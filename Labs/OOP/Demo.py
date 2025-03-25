class SimpleClass:
    __counter = 0
    def __init__(self):
        self.__name = "SimpleClass"

    def get_name(self):
        self.author = "Author"
        return self.__name, self.author

    

simpleclass = SimpleClass()
simpleclass._SimpleClass__name = "SimpleClass2"
print(simpleclass._SimpleClass__name)
print(simpleclass.get_name())

print(simpleclass._SimpleClass__counter)