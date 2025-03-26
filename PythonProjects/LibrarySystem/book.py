from publication import Publication

class Book(Publication):
    '''
    The Book class is a subclass of the Publication class. \n
    It inherits the attributes and methods of the Publication class. \n
    The Book class has the following additional attributes: \n'''
    def __init__(self, publication_id, title, publisher, publication_year, publication_type, author, isbn, pages):
        super().__init__(publication_id, title, publisher, publication_year, publication_type)
        self.author = author
        self.isbn = isbn
        self.pages = pages

    def display(self):
        '''
        The display method displays the details of the book. \n
        It prints the publication_id, title, publisher, publication_year, \n
        publication_type, author, isbn, and pages of the book. \n
        '''
        print('Publication ID:', self.publication_id)
        print('Title:', self.title)
        print('Publisher:', self.publisher)
        print('Publication Year:', self.publication_year)
        print('Publication Type:', self.publication_type)
        print('Author:', self.author)
        print('ISBN:', self.isbn)
        print('Pages:', self.pages)

    def calculate_late_fee(self, days):
        '''
        The calculate_late_fee method calculates the late fee for the book. \n
        It takes the number of days the book is late as a parameter and \n
        returns the late fee based on the number of days. \n
        The late fee for a book is $0.25 per day. \n
        '''
        return days * 0.25