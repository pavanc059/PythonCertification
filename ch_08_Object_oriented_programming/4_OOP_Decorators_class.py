class SimpleDecorator:
    def __init__(self, own_function):
        self.func = own_function

    def __call__(self, *args, **kwargs):
        print('"{}" was called with the following arguments'.format(self.func.__name__))
        print('\t{}\n\t{}\n'.format(args, kwargs))
        result = self.func(*args, **kwargs)
        print('Decorator is still operating')
        return result


@SimpleDecorator
def combiner(*args, **kwargs):
    return "\tHello from the decorated function; received arguments:", args, kwargs

print(combiner('a', 'b', exec='yes'))