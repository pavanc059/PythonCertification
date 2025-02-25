from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self):
        pass

class Rectangle(Shape):
    def __init__(self, width, height):
        self.width = width
        self.height = height
         
    def area(self):
        return self.width * self.height

class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius
    
    def area(self):
        return 3.14 * self.radius * self.radius

class Triangle(Shape):
    def __init__(self, base, height):
        self.base = base
        self.height = height
   
    def area(self):
        return 0.5 * self.base * self.height

# Using polymorphism
shapes = [Rectangle(5, 3), Circle(2), Triangle(10, 15)]
for shape in shapes:
    print(shape.area())
