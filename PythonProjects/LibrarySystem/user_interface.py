class UserInterface:
    def display_menu(self):
        print("Welcome to the Library System!")
        print("1. View Books")
        print("2. Add Book")
        print("3. Remove Book")
        print("4. Add Publication")
        print("5. Remove Publication")
        print("6. View Publications")
        print("7. Search Publication by title or author")
        print("8. Search book or books by title or author")
        print("9. Search multiple books by title or author")
        print("10. Exit")

    def get_user_choice(self):
        choice = input("Please enter your choice: ")
        return choice

    def display_books(self, books):
        if not books:
            print("No books available.")
        else:
            for book in books:
                print(f"Title: {book['title']}, Author: {book['author']}")

    def get_book_details(self):
        title = input("Enter book title: ")
        author = input("Enter book author: ")
        return {"title": title, "author": author}

    def display_message(self, message):
        print(message)