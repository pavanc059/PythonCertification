# create custom sequences and mappings using magic methods like __getitem__ and __len__ to make them behave like built-in sequences and mappings.
# implement following methods .__getitem__(), __len__() .__contains__() and __reversed__()
# .__getitem__() - Access elements using indexing and slicing. like my_sequence[0] or my_sequence[1:4]
# .__len__() - Return the number of elements in the sequence or mapping. like len(my_sequence)
# .__contains__() - Check if an element exists in the sequence or mapping. like 3 in my_sequence
# .__reversed__() - Return an iterator that iterates over the elements in reverse order. like reversed(my_sequence)
class OnlineBooksCatalog:

    __available_books = ["Don Quixote", "A Tale of Two Cities", "The Great Gatsby", "Moby Dick", 
                         "War and Peace", "Pride and Prejudice", "The Catcher in the Rye", "The Lord of the Rings", "To Kill a Mockingbird", 
                         "1984", "Brave New World", "The Hobbit", "Fahrenheit 451", "Jane Eyre", "Wuthering Heights", "The Odyssey", "Crime and Punishment", 
                         "The Brothers Karamazov", "Anna Karenina", "The Divine Comedy"]

    def __init__(self):
        self.books = OnlineBooksCatalog.__available_books.copy()

    @classmethod
    def add_book(cls, book_title):
        cls.__available_books.append(book_title)

    def __getitem__(self, index):
        return self.books[index]
    
    def __len__(self):
        return len(self.books)
    
    def __contains__(self, item):
        return item in self.books
    
    def __reversed__(self):
        return reversed(self)
    