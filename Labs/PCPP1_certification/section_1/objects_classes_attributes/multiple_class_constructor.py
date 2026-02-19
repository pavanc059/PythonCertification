class PizzaWithKeywordArguments:
    __allowed_sizes = [10, 12, 14] # Class attribute (private class attribute)

    def __init__(self, *, pizza_size, toppings=None): # '*' indicates that any parameters after this must be passed as a keyword argument only
        print("2.Object initialization")
        print(f"Pizza size: {pizza_size}, Toppings: {toppings}")
        if pizza_size not in self.__allowed_sizes:
            raise ValueError(f"Pizza size must be one of {self.__allowed_sizes}")
        self.size = pizza_size
        self.toppings = toppings if toppings is not None else []
        self.extra_cheese = False
        self.price = None

class PizzaWithAnyArguments:
    __allowed_sizes = [10, 12, 14] # Class attribute (private class attribute)

    def __init__(self, *args, **kwargs): # Positional arguments
        print("2.Object initialization")
        pizza_size = args[0] if args else None
        toppings = kwargs.get("toppings", None)
        print(f"Pizza size: {pizza_size}, Toppings: {toppings}")
        if pizza_size not in self.__allowed_sizes:
            raise ValueError(f"Pizza size must be one of {self.__allowed_sizes}")
        
        if kwargs:
            for key, value in kwargs.items():
                print(f"{key}: {value}")
                setattr(self, key, value)
        self.size = pizza_size
        self.toppings = toppings if toppings is not None else []
        self.extra_cheese = False
        self.price = None
        
class PizzaWithClassMethod:
    __allowed_sizes = [10, 12, 14] # Class attribute (private class attribute)

    def __init__(self, pizza_size, toppings=None):
        print("2.Object initialization")
        print(f"Pizza size: {pizza_size}, Toppings: {toppings}")
        if pizza_size not in self.__allowed_sizes:
            raise ValueError(f"Pizza size must be one of {self.__allowed_sizes}")
        self.size = pizza_size
        self.toppings = toppings if toppings is not None else []
        self.extra_cheese = False
        self.price = None

    @classmethod
    def create_pizza(cls, pizza_size, toppings=None):
        print("3. Call the class method")
        return cls(pizza_size, toppings)
    
    @classmethod
    def create_pizza_with_extra_cheese(cls, pizza_size, toppings=None, extra_cheese=False):
        print("4. Call the class method with extra cheese")
        pizza = cls(pizza_size, toppings)
        pizza.extra_cheese = extra_cheese
        print(f"Extra cheese added: {pizza.extra_cheese} and Pizza is : {pizza.__dict__}")
        return pizza

    @classmethod
    def create_pizza_with_default_price(cls, pizza_size, toppings=None, price=15):
        print("5. Call the class method with default price")
        pizza = cls(pizza_size, toppings)
        pizza.price = price
        return pizza

if __name__ == "__main__":
    veggie_pizza = PizzaWithKeywordArguments(pizza_size=12) # instantiation and initialization
    print(veggie_pizza.__dict__) # Accessing instance attributes using __dict__

    veggie_pizza = PizzaWithKeywordArguments(pizza_size=12, toppings=["jalapenos", "cheese"]) # instantiation and initialization
    print(veggie_pizza.__dict__) # Accessing instance attributes using __dict__
    
    pizza_with_args = PizzaWithAnyArguments(12, toppings=["mushrooms", "peppers"]) # instantiation and initialization
    print(pizza_with_args.__dict__) # Accessing instance attributes using __dict__

    pizza_with_args2 = PizzaWithAnyArguments(14, toppings=["olives", "onions"], extra_cheese=True, Is_thin_crust=True, pizza_type="italian") # instantiation and initialization
    print(pizza_with_args2.Is_thin_crust)
    print(pizza_with_args2.__dict__) # Accessing instance attributes using __dict__

    pizza_from_class_method = PizzaWithClassMethod.create_pizza(12, toppings=["pepperoni", "sausage"]) # instantiation using class method
    print(pizza_from_class_method.__dict__) # Accessing instance attributes using __dict__
    new_pizza = pizza_from_class_method.create_pizza_with_extra_cheese(14, toppings=["bacon", "ham"], extra_cheese=True) # instantiation using class method with extra cheese
    print(new_pizza.extra_cheese) # Accessing instance attribute
    print(new_pizza.__dict__) # Accessing instance attributes using __dict__