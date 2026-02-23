# Implement an iterable class that generates the Fibonacci sequence up to a given limit by implementing __iter__ and __next__ methods to make it an iterable.
# create a iterator using __iter_ method.

class Fibonacci:
    def __init__(self, max_number):
        self.current, self.next = 1, 1
        self.max_number = max_number
        self.counter = 1

    def __iter__(self):
        return self
    
    def __next__(self):
        if self.counter >= self.max_number:
            raise StopIteration
                
        value = self.current
        self.current, self.next = self.next, self.current + self.next
        self.counter += 1
        return value


class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __str__(self):
        return f"Hello, my name is {self.name} and I am {self.age} years old."
    
class PersonList:
    def __init__(self, *args:Person):
        self.persons = [*args]
        self.counter = 0

    def __iter__(self):
        return self
    
    def __next__(self):        
        
        if self.counter >= len(self.persons):
            raise StopIteration
        
        value = self.persons[self.counter]
        self.counter += 1
        return value

class PersonIterable:
    def __init__(self, *args:Person):
        self.persons = [*args]

    def __iter__(self):
        return iter(self.persons)

