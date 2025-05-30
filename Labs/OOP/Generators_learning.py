import tokenize
import tabnanny
import cProfile

class NumberIterator:
    def __init__(self, number):
        self.number = number
        self.current = 1

    def __iter__(self):
        return self
    
    def __next__(self):
        if self.current <= self.number:
            result = self.current
            self.current += 1
            return result
        else:
            raise StopIteration
        

for number in NumberIterator(50):
    print(number)

'''
If you invoke the fib() function, it will return a generator object.
You can then use the next() function to get the next value from the generator.
You can also use a for loop to iterate through the generator.

'''
def fib():
    a, b = 0, 1
    while True:
       
       a, b = b, a+b
       (yield b)

for i, number in enumerate(fib()):
    if i > 50:
        break
    print(number)

# following code will print only first number in the sequence as we're creating a new generator object each time
print(next(fib()))
print(next(fib()))
print(next(fib()))
print(next(fib()))

# following code will print first 5 number in the sequence as we're single generator object and using it.
fib = fib()
print(next(fib))
print(next(fib))
print(next(fib))
print(next(fib))

cProfile.run('sum([i * 2 for i in range(100000)])')

cProfile.run('sum((i * 2 for i in range(100000)))')

letters = ["A", "B", "C", "D", "E"]

it = iter(letters)

while True:
    try:
        letter = next(it)
        print(letter)
    except StopIteration:
        break