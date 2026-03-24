# lambda x: x + 1
# lambda x, y: x * y
# (lambda x: x + 1)(2)  # Output: 3
# (lambda x, y: x * y)(3, 4)  # Output: 12
# (lambda x: "even" if x % 2 == 0 else "odd")(5)  # Output: "odd"
# (lambda x: (x, x+1))(10)  # Output: (10, 11)
# x= 5 
# z= 5
# (lambda x:x+z)(x)  # Output: 10
# Map Example map(callable, iterable)
# list(map(lambda x: x + 1, [1, 2, 3]))  # Output: [2, 3, 4]
# Filter Example filter(function, iterable)
# list(filter(lambda x: x % 2 == 0, [1, 2, 3, 4, 5]))  # Output: [2, 4]
# reduce Example from functools import reduce recude(function, iterable[, initializer])

def filter_uppercase(strings):
    return list(filter(lambda x: x.isupper(), strings))

test = ['hello', 'world', 'PYTHON', 'programming']
result = filter_uppercase(test)
print(result)  # Output: ['hello', 'world', 'PYTHON', 'program