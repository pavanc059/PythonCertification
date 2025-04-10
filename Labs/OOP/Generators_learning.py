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