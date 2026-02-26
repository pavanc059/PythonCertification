from book import Book

class Novel(Book):
    '''
    The Novel class is a subclass of the Book class. \n
    It inherits the attributes and methods of the Book class. \n
    The Novel class has the following additional attributes: \n
    genre: The genre of the novel (e.g., fiction, mystery, romance). \n
    '''
    def __init__(self, publication_id, title, publisher, publication_year, publication_type, author, isbn, pages, genre):
        super().__init__(publication_id, title, publisher, publication_year, publication_type, author, isbn, pages)
        self.genre = genre

    def display(self):
        '''
        The display method displays the details of the novel. \n
        It prints the publication_id, title, publisher, publication_year, \n
        publication_type, author, isbn, pages, and genre of the novel. \n
        '''
        super().display()
        print('Genre:', self.genre)
