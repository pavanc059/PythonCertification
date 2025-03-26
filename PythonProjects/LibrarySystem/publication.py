
'''
Following import statement imports the ABC class from the abc module.
ABC stands for Abstract Base Class. It is a built-in Python \n
module that provides a metaclass for defining abstract base classes.
'''
from abc import ABC, abstractmethod


class Publication(ABC):
    '''        
    Publications are the items that are available in the library. \n
    These items can be books, journals, magazines, etc. \n
    The Publication class is an abstract class that contains the \n
    attributes and methods that are common to all types of publications. \n
    The Publication class has the following attributes: \n
    publication_id: A unique identifier for the publication. \n
    title: The title of the publication. \n
    publisher: The publisher of the publication. \n
    publication_year: The year in which the publication was published. \n
    publication_type: The type of the publication (e.g., book, journal, magazine). \n
    The Publication class has the following methods: \n
    display: An abstract method that displays the details of the publication. \n
    calculate_late_fee: An abstract method that calculates the late fee for the publication. \n
    '''
    def __init__(self, publication_id, title, publisher, publication_year, publication_type):
        self.publication_id = publication_id
        self.title = title
        self.publisher = publisher
        self.publication_year = publication_year
        self.publication_type = publication_type

    @abstractmethod
    def display(self):
        pass

    @abstractmethod
    def calculate_late_fee(self, days):
        pass