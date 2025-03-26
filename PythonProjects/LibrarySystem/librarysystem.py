from librarymember import LibraryMember
from publication import Publication


class LibrarySystem():

    

    def __init__(self, libraryId):
        self.libraryId = libraryId
        self.members = {}
        self.publications = {}
        self.__publication_id = 0

    @classmethod
    def create_library(cls, libraryId):
        return cls(libraryId)
    
    @classmethod
    def create_member(cls, name, address, phone, email):
        cls.__member_id += 1
        return LibraryMember(name, address, phone, email)

    def add_member(self, member):
        if not isinstance(member, LibraryMember):
            raise ValueError('member must be a LibraryMember object')
        


        self.members.append(member)


    def add_publication(self, publication):
        if not isinstance(publication, Publication):
            raise ValueError('publication must be a Publication object')
        self.publications.append(publication)

    def process_borrowing(self, member, publication):
        if not isinstance(member, LibraryMember):
            raise ValueError('member must be a LibraryMember object')
        if not isinstance(publication, Publication):
            raise ValueError('publication must be a Publication object')
        
        if member in self.members and publication in self.publications:
            for member in self.members:
                if member == member:
                    member.borrow_item(publication)
                    publication.borrowed = True      
        member.borrow_item(publication)
        publication.borrowed = True

    def process_returning(self, member, publication):
        if not isinstance(member, LibraryMember):
            raise ValueError('member must be a LibraryMember object')
        if not isinstance(publication, Publication):
            raise ValueError('publication must be a Publication object')
        member.return_item(publication)
        publication.borrowed = False

    def display_members(self):
        for member in self.members:
            print(member)

    def display_publications(self):
        for publication in self.publications:
            publication.display()
            print('\n')

    def display_report(self):
        for member in self.members:
            print(member)
            for item in member:
                print(item)
            print('\n')
       