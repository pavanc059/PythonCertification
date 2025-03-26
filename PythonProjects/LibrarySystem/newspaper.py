from periodical import Periodical

class Newspaper(Periodical): 
    '''
    The Newspaper class is a subclass of the Periodical class. \n
    It
    inherits the attributes and methods of the Periodical class. \n''
    'The Newspaper class has the following additional attributes: \n''
    '''
    def __init__(self, publication_id, title, publisher, publication_year, publication_type, issue_number, frequency, section):
        super().__init__(publication_id, title, publisher, publication_year, publication_type, issue_number, frequency)
        self.section = section


    def display(self):
        '''
        The display method displays the details of the newspaper. \n
        It prints the publication_id, title, publisher, publication_year, \n
        publication_type, issue_number, frequency, and section of the newspaper. \n
        '''
        print('Publication ID:', self.publication_id)
        print('Title:', self.title)
        print('Publisher:', self.publisher)
        print('Publication Year:', self.publication_year)
        print('Publication Type:', self.publication_type)
        print('Issue Number:', self.issue_number)
        print('Frequency:', self.frequency)
        print('Section:', self.section)