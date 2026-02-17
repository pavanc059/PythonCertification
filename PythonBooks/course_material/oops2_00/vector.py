# vector.py

class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, obj):
        return Vector(self.x + obj.x, self.y + obj.y)

    def __repr__(self):
        return f"Vector({self.x}, {self.y})"
