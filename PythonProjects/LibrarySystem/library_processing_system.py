
from publication import Publication
from book import Book
from librarymember import LibraryMember
from librarysystem import LibrarySystem

if __name__ == "__main__":
    
    # Create a book
    book1 = Book(1, 'Python Programming', 'John Doe', 2021, 'Non-Fiction', 'John Doe', '025-0-0325-1416-1',300)
    #book1.display()
    print('\n')

    book2 = Book(2, 'Java Programming', 'Jane Doe', 2021, 'Non-Fiction', 'John Doe', '025-0-0325-1416-2',400)
    #book2.display()
    print('\n')

    book3 = Book(3, 'C++ Programming', 'John Smith', 2021, 'Non-Fiction', 'John Doe', '025-0-0325-1416-3',500)
    #book3.display()
    print('\n')

    book4 = Book(4, 'JavaScript Programming', 'Jane Smith', 2021, 'Non-Fiction', 'John Doe', '025-0-0325-1416-4',600)
    #book4.display()
    print('\n')

    book5 = Book(5, 'HTML Programming', 'John Doe', 2021, 'Non-Fiction', 'John Doe', '025-0-0325-1416-5',700)
    #book5.display()
    print('\n')

    # Create a library member
    member1 = LibraryMember(1, 'John Bond', '123 Main St', '555-555-5555', 'john@test.com')
    member2 = LibraryMember(2, 'Stacy moss', '326 Lake dr', '555-555-7895', 'moss@test.com')
    
    # Library system
    libraryatmain = LibrarySystem(1)
    libraryatmain.add_member(member1)
    libraryatmain.add_member(member2)
    libraryatmain.add_publication(book1)
    libraryatmain.add_publication(book2)
    libraryatmain.add_publication(book3)
    libraryatmain.add_publication(book4)
    libraryatmain.add_publication(book5)


    # Process borrowing
    libraryatmain.process_borrowing(member1, book1)
    libraryatmain.process_borrowing(member2, book2)
    libraryatmain.process_borrowing(member1, book3)
    libraryatmain.process_borrowing(member2, book4)
    libraryatmain.process_borrowing(member1, book5)
    print('\n')
    print('=================  Members    ============================')

    # Display members
    libraryatmain.display_members()
    print('\n')
    print('====================   Publications =========================')
    
    # Display publications
    libraryatmain.display_publications()
    print('\n')
    print('========================= Display what each member got  ====================')

    # Display what each member got
    
    libraryatmain.display_report()
    print('\n')
        
   

    # Create a library member
    # member1 = LibraryMember(1, 'John Doe', '123 Main St', '555-555-5555', '


    


