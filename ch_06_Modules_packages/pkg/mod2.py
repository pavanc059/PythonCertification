def clean_data():
    print("Data cleaned from mod2")

class location:
    def __init__(self, city, country):
        self.city = city
        self.country = country

    def display(self):
        print(f"Location: {self.city}, {self.country}")