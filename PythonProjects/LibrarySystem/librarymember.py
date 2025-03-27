from typing import List, Optional
from publication import Publication
class LibraryMember:
    def __init__(self, memberId, name, address, phone, email, borrowed_items: Optional[List[Publication]] = None):
        self.memberId = memberId
        self.name = name
        self.address = address
        self.phone = phone
        self.email = email
        self.borrowed_items = borrowed_items if borrowed_items is not None else []
        self.__index = 0

    def __str__(self):
        return f'{self.name} lives at {self.address} and can be reached at {self.phone} and Member ID: {self.memberId}'
    
    def borrow_item(self, item):
        self.borrowed_items.append(item)

    def return_item(self, item):
        self.borrowed_items.remove(item)
        print(f'{self.name} has returned {item.title}')

    def display_info(self):
        print(f'Member ID: {self.memberId}')
        print(f'Name: {self.name}')
        print(f'Address: {self.address}')
        print(f'Phone: {self.phone}')
        print(f'Email: {self.email}')

    def __iter__(self):
        return self
    

    def __next__(self):
        if self.__index == len(self.borrowed_items):
            self.__index = 0
            raise StopIteration
        item =self.borrowed_items[self.__index]
        self.__index += 1
        return f'Borrowed book : {item.title}'
    
    
    
        

    