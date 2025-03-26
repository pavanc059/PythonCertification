[Publication (Abstract Class)]
- publication_id: str
- title: str
- publisher: str
+ display_info()
+ calculate_late_fee()

    ↑ (Inheritance)
    
[Book]                [Periodical]
- author: str        - issue_number: int
- isbn: str          - publication_date: date
- pages: int         + display_info()
+ display_info()     
+ calculate_late_fee()

    ↑ (Inheritance)   ↑ (Inheritance)
    
[Magazine]            [Newspaper]
- category: str       - section: str
+ display_info()      + display_info()

[LibraryMember]
- member_id: str
- name: str
- borrowed_items: List
+ borrow_item()
+ return_item()
+ display_info()

[LibrarySystem]
- members: List
- publications: List
+ add_member()
+ remove_member()
+ add_publication()
+ process_borrowing()
+ process_return()

## This implementation demonstrates:

- Abstraction : Using abstract base class Publication with abstract methods

- Encapsulation : Private attributes with underscore prefix

- Inheritance : Class hierarchy (Publication → Book/Periodical → Magazine)

- Polymorphism : Different implementations of display_info() and calculate_late_fee()

- Composition : LibrarySystem contains Members and Publications

## Additional OOP concepts demonstrated:

- Method overriding

- Super() method usage

- Type hints

- List comprehensions

- Property decorators (can be added for getter/setter methods)

- Interface-like behavior through abstract base classes

- This project can be extended with features like:

- Reservation system

- Multiple copies of publications

- Member categories with different borrowing privileges

- Fine payment system

- Search functionality

- Report generation