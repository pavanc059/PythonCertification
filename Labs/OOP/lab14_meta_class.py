from datetime import datetime

def get_instantiation_time(self):
    return self.instantiation_time

class Meta_class(type):
    classNames = []
    
    def __new__(mcs, name, bases, dictionary):
        Meta_class.classNames.append(name)
        now = datetime.now()
        dictionary['instantiation_time'] = datetime.timestamp(now)
        if get_instantiation_time not in dictionary:
            dictionary['get_instantiation_time'] = get_instantiation_time
        obj = super().__new__(mcs, name, bases, dictionary)
        
        
        return obj

class myClass3(metaclass=Meta_class):
    pass
         
class myClass1(metaclass=Meta_class):
    pass

class myClass2(metaclass=Meta_class):
    pass


myobj1 = myClass1()
myObj3 = myClass3()
myObj2 = myClass2()
print(myobj1.get_instantiation_time())
print(myObj2.get_instantiation_time())
print(myObj3.get_instantiation_time())
print(Meta_class.classNames)