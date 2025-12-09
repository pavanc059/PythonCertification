class Fib:
	def __init__(self, nn):
		self.__n = nn
		self.__i = 0
		self.__p1 = self.__p2 = 1

	def __iter__(self):
		print("Fib iter")
		return self

	def __next__(self):
		self.__i += 1
		if self.__i > self.__n:
			raise StopIteration
		if self.__i in [1, 2]:
			return 1
		ret = self.__p1 + self.__p2
		self.__p1, self.__p2 = self.__p2, ret
		return ret

for i in Fib(5):
    print(i)
class Class:
	def __init__(self, n):
		self.__iter = Fib(n)

	def __iter__(self):
		print("Class iter")
		return self.__iter;

def fun(n):
    print('Function entered')
    for i in range(n):
        yield i
    print('Function exited')
    
for i in fun(5):
    pass #print(i)

def powersOf2(n):
    pow = 1
    for i in range(n):
        yield pow
        pow *= 2

for v in powersOf2(8):
    pass #print(v)

t = [x for x in powersOf2(5)]
#print(t)

t = list(powersOf2(3))
#print(t)

def powersOf2(n):
    pow = 1
    for i in range(n):
        yield pow
        pow *= 2

for i in range(20):
    if i in powersOf2(4):
        pass #print(i)



object = Class(8)

for i in object:
	pass #print(i)


#Fibonacci number generator
def fib(n):
    p1 = p2 = 1
    for i in range(n):
        if i in [1, 2]:
            yield 1
        else:
            ret = p1 + p2
            p1, p2 = p2, ret
            yield ret

for i in fib(5):
    print(i)

def f():
    try:
        yield 1
        try:
            yield 2
            1/0
            yield 3  # never get here
        except ZeroDivisionError:
            yield 4
            yield 5
            raise
        except:
            yield 6
        yield 7     # the "raise" above stops this
    except:
       yield 8
    yield 9
    try:
        x = 12
        yield x
    finally:
       yield 10
    yield 11

print(list(f()))