# positive.py

class PositiveInteger:
    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, instance, owner):
        print(f"Getting {self._name}")
        return instance.__dict__[self._name]

    def __set__(self, instance, value):
        print(f"Setting {self._name} to {value}")
        if not isinstance(value, int ) or value <= 0:
            raise ValueError("Positive integer required")

        instance.__dict__[self._name] = value


class Ellipse:
    width = PositiveInteger()
    height = PositiveInteger()

    def __init__(self, width, height):
        self.width = width
        self.height = height
