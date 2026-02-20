class Pizza():

    __allowed_sizes = [14, 16, 18]

    def __new__(cls, pizza_size, toppings):
        print("1.object Creation")
        if pizza_size not in cls.__allowed_sizes:
            raise Exception('Minimum pizza size allowed is 14"')
        if not toppings:
            raise Exception('At least one topping must be provided')
        return super().__new__(cls)
    
    def __init__(self, pizza_size, toppings):
        print("2.Object initialization")
        self.size = pizza_size
        self.toppings = toppings
        self.extra_cheese = False
        self.price = None
    
    @property
    def price(self):
        return self._price
    
    @price.setter
    def price(self, value):
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            raise ValueError("Price must be a non-negative number")        
        self._price = self.calculate_price()

    @property
    def extra_cheese(self):
        if not hasattr(self, '_extra_cheese'):
            return None
        return self._extra_cheese

    @extra_cheese.setter
    def extra_cheese(self, value):
        if not isinstance(value, bool):
            raise ValueError("extra_cheese must be a boolean value")
        self.calculate_price()
        self._extra_cheese = value

    # def __call__(self, *args, **kwds):
    #     print("3. Call the class")
        
    def calculate_price(self):
        base_price = 10
        size_price = (self.size - 14) * 2
        toppings_price = len(self.toppings) * 1.5
        extra_cheese_price = 2 if self.extra_cheese else 0
        return base_price + size_price + toppings_price + extra_cheese_price

    def describe_pizza(self):
        return f'{self.size} pizza with {", ".join(self.toppings)} and price ${self.price:.2f}'

    def __str__(self):
        return f'{self.size} pizza with {", ".join(self.toppings)} and price ${self.price:.2f}'
  


