import datetime


def executiontime_decorator(func):
    def internal_wrapper(*args, **kwargs):
        start_time = datetime.datetime.now()
        print(f"Start of execution {func.__name__} arguments {args}: {datetime.date.strftime(start_time, "%d/%m/%Y, %H:%M:%S")} ")        
        result = func(*args, **kwargs)
        end_time = datetime.datetime.now()
        print(f"End of execution {func.__name__} arguments {args} : {datetime.date.strftime(end_time, "%d/%m/%Y, %H:%M:%S")} ")
        return result
    return internal_wrapper
    
@executiontime_decorator
def addition(a, b):
    return a + b

@executiontime_decorator
def multiplication(a, b):
    return a * b


multiplication(5, 10)
addition(5, 10)
multiplication(15, 25)
addition(15, 25)
addition(25, 35)
multiplication(25, 35)
addition(35, 45)
multiplication(35, 45)
addition(45, 55)
multiplication(45, 55)