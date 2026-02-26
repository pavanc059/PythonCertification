# abcshape.py

from abc import ABC, abstractmethod
import math

class Shape(ABC):
    def __init__(self, red, green, blue):
        self.red = red
        self.green = green
        self.blue = blue

    @abstractmethod
    def get_area(self):
        pass

    def hex_color(self):
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"


class Circle(Shape):
    def __init__(self, radius, red, green, blue):
        self.radius = radius
        super().__init__(red, green, blue)

    def get_area(self):
        return math.pi * pow(self.radius, 2)


class Square(Shape):
    pass
