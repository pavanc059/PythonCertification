from librarymember import LibraryMember
from publication import Publication


class LibrarySystem():
    __member_id = 0 

    def __init__(self, libraryId):
        self.libraryId = libraryId
        self.members = {}
        self.publications = []

    def __str__(self):
        return f'Library ID: {self.libraryId, self.__library_name, self.__library_address, self.__library_phone, self.__library_email}'

    @classmethod
    def create_library(cls, libraryId, libraryName, libraryAddress, libraryPhone, libraryEmail):
        cls.__library_name = libraryName
        cls.__library_address = libraryAddress
        cls.__library_phone = libraryPhone
        cls.__library_email = libraryEmail
        cls.members = {}
        cls.publications = []
        return cls(libraryId)
    
    @classmethod
    def create_member(cls, name, address, phone, email):
        cls.__member_id = LibrarySystem.__member_id + 1
        print(cls.__member_id)
        return LibraryMember(cls.__member_id, name, address, phone, email)
    
    @staticmethod
    def dateDifference(date1, date2):
        return date1 - date2
      
    def add_member(self, member):
        if not isinstance(member, LibraryMember):
            raise ValueError('member must be a LibraryMember object')        
        member = LibrarySystem.create_member(member.name, member.address, member.phone, member.email)
        self.members[member.memberId] = member

    def add_publication(self, publication):
        if not isinstance(publication, Publication):
            raise ValueError('publication must be a Publication object')        
        self.publications.append(publication)

    def process_borrowing(self, member, publication):
        if not isinstance(member, LibraryMember):
            raise ValueError('member must be a LibraryMember object')
        if not isinstance(publication, Publication):
            raise ValueError('publication must be a Publication object')
        
        if member.memberId in self.members.keys() and publication in self.publications:
            for memberId, localmember in self.members.items():
                if memberId == member.memberId:
                    localmember.borrow_item(publication)
                    publication.borrowed = True
                    self.members[member.memberId] = localmember 
                    print(f'{member.name} has borrowed {publication.title}')     
        
    def process_returning(self, member, publication):
        if not isinstance(member, LibraryMember):
            raise ValueError('member must be a LibraryMember object')
        if not isinstance(publication, Publication):
            raise ValueError('publication must be a Publication object')
        member.return_item(publication)
        publication.borrowed = False

    def display_members(self):
        for memberId, member in self.members.items():
            print(f'Membership ID: {memberId}')
            print('\n')
            member.display_info()

    def display_publications(self):
        for publication in self.publications:
            publication.display()
            print('\n')

    def display_report(self):
        for memberId, member in self.members.items():
            print(member)
            print('\n')
            for item in member:
                print(item)
            print('\n')
       