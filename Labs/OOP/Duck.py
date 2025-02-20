class Duck:
    #class variable
    species = 'Bird'

    def __init__(self, name, age, height, weight, color):
        #instance variables 
        self.name = name
        self.age = age
        self.height = height
        self.weight = weight
        self.color = color

    def walk(self):
        print('I am walking')

    def quack(self):
        return print('Quack')
    

duck = Duck('Duck', 1, 10, 10, 'white')
drake = Duck('Drake', 2, 20, 20, 'black')
hen = Duck('Hen', 3, 30, 30, 'brown')

print(f'Before setting attribute {getattr(duck, 'height')}')
# Before setting attribute 10
setattr(duck, 'height', 100)
print(f'Instance Variable {drake.height}')
# Instance Variable 20
print(f'After setting attribute {getattr(duck, 'height')}')
# After setting attribute 100
print(f'Content of object {duck.__dict__}')
# Content of object {'name': 'Duck', 'age': 1, 'height': 100, 'weight': 10, 'color': 'white'}
print(f'Content of object {Duck.__dict__}')
#{'__module__': '__main__', 'species': 'Bird', '__init__': <function Duck.__init__ at 0x0000015C3399E160>, 
# 'walk': <function Duck.walk at 0x0000015C3399D260>, 'quack': <function Duck.quack at 0x0000015C3399EDE0>, 
# '__dict__': <attribute '__dict__' of 'Duck' objects>, '__weakref__': <attribute '__weakref__' of 'Duck' objects>, '__doc__': None}