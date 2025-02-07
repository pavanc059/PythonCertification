class Test:
    def __init__(self):
        self.i = 0
        self.title = 'Python'

    def __iter__(self):
        yield 10 #return self #return with used with __next__ method

    def __next__(self):
        self.i += 1
        if self.i > 50:
            raise StopIteration
        return self

    def __repr__(self):
        print('from repr')
        return 'Test(i=%r, author=%r)' % (self.i, self.title)
    
    # def __str__(self):
    #     print('from str')
    #     return 'THis class is example of yield'

for i in Test():
    print(i)

print(Test())

'''
output :
50
from repr
Test(i=0, author='Python')
'''