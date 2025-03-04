from datetime import datetime

def printFunctionExecutionTime(fun):
    def wrapper(*args, **kwargs):
        start = datetime.now()
        result = fun(*args, **kwargs)
        print("Function execution time: ", datetime.now() - start)
        print(f"function {fun.__name__} started at {start.strftime('%Y-%m-%d %H:%M:%S')} and ended at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return result
    return wrapper

@printFunctionExecutionTime
def add(a, b):
    return a + b

@printFunctionExecutionTime
def multiply(a, b):
    return a * b

print(add(1, 2))  
print(multiply(1, 2))
