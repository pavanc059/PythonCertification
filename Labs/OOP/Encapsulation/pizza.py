class Pizza:
    def __init__(self, toppings):
        self.toppings = toppings

    def __repr__(self):
        return f"Pizza ({self.toppings})"
    
    def __str__(self):
        return f"Pizza ({self.toppings}) from string method"
    
veg_pizza = Pizza(["tomatoes", "onions"])
print(repr(veg_pizza))
#print(veg_pizza)