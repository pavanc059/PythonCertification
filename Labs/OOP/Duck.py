class Duck:
    def __init__(self, name, age, height, weight, color):
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
setattr(duck, 'height', 100)
print(f'After setting attribute {getattr(duck, 'height')}')