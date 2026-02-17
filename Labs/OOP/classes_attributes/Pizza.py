class Pizza:
    def __init__(self, size, toppings):
        self.size = size
        self.toppings = toppings
        self.extra_cheese = False

    @property
    def extra_cheese(self):
        return self._extra_cheese
    
    @extra_cheese.setter
    def extra_cheese(self, value):
        print(f'Setting extra cheese to {value}')
        if not isinstance(value, bool):
            raise ValueError("Extra cheese value must be a boolean")
        self._extra_cheese = value
    
    def describe_pizza(self):
        return f'{self.size} pizza with {", ".join(self.toppings)}'
    
viggie_pizza = Pizza('large', ['olives', 'mushrooms', 'peppers'])
print(viggie_pizza.describe_pizza())

#viggie_pizza.extra_cheese = True
#viggie_pizza._extra_cheese = False
print(f'Extra cheese: {viggie_pizza.extra_cheese}')