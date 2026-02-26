def load_data():
    print("Data loaded from mod1")

class Customer:
    def __init__(self, name):
        self.name = name

    def greet(self):
        print(f"Hello, {self.name}!")