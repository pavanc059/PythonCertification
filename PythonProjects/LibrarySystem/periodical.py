from publication import Publication

class Periodical(Publication):
    '''
    The Periodical class is a subclass of the Publication class. \n
    It inherits the attributes and methods of the Publication class. \n
    The Periodical class has the following additional attributes: \n
    '''
    def __init__(self, publication_id, title, publisher, publication_year, publication_type, issue_number, frequency):
        super().__init__(publication_id, title, publisher, publication_year, publication_type)
        self.issue_number = issue_number
        self.frequency = frequency

    def display(self):
        '''
        The display method displays the details of the periodical. \n
        It prints the publication_id, title, publisher, publication_year, \n
        publication_type, issue_number, and frequency of the periodical. \n
        '''
        print('Publication ID:', self.publication_id)
        print('Title:', self.title)
        print('Publisher:', self.publisher)
        print('Publication Year:', self.publication_year)
        print('Publication Type:', self.publication_type)
        print('Issue Number:', self.issue_number)
        print('Frequency:', self.frequency)

    def calculate_late_fee(self, days):
        '''
        The calculate_late_fee method calculates the late fee for the periodical. \n
        It takes the number of days the periodical is late as a parameter and \n
        returns the late fee based on the number of days. \n
        The late fee for a periodical is $0.50 per day. \n
        '''
        return days * 0.50