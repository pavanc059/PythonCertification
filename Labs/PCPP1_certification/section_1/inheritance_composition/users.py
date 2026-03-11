class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def introduce(self):
        return f"Hello, my name is {self.name} and I am {self.age} years old."
    
class Student(Person):
    def __init__(self, name, age, student_id):
        super().__init__(name, age)
        self.student_id = student_id

    def introduce(self):
        base_introduction = super().introduce()
        return f"{base_introduction} I am a student with ID {self.student_id}."
    
class Teacher(Person):
    def __init__(self, name, age, subject):
        super().__init__(name, age)
        self.subject = subject

    def introduce(self):
        base_introduction = super().introduce()
        return f"{base_introduction} I am a teacher of {self.subject}."
    
class SchoolStaff(Person):
    def __init__(self, name, age, position):
        super().__init__(name, age)
        self.position = position

    def introduce(self):
        base_introduction = super().introduce()
        return f"{base_introduction} I work as a {self.position} at the school."
    

