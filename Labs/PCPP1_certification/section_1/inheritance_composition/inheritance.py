class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def introduce(self):
        return f"Hello, my name is {self.name} and I am {self.age} years old."

class Employee(Person):
    def __init__(self, name, age, employee_id):
        super().__init__(name, age) # Call the parent class's __init__ method to initialize name and age
        self.employee_id = employee_id

    def introduce(self):
        parent_introduction = super().introduce() # Call the parent class's introduce

class Student(Person):
    def __init__(self, name, age, student_id):
        super().__init__(name, age) # Call the parent class's __init__ method to initialize name and age
        self.student_id = student_id

    def introduce(self):
        parent_introduction = super().introduce() # Call the parent class's introduce
        return f"{parent_introduction} My student ID is {self.student_id}."
    
class Teacher(Employee):
    __employee_id_counter = 1000 # Class variable to keep track of employee IDs
    def __init__(self, name, age, subject):
        Teacher.__employee_id_counter += 1 # Increment the employee ID counter
        employee_id = Teacher.__employee_id_counter # Assign the new employee ID
        super().__init__(name, age, employee_id) # Call the parent class's __init__ method to initialize name and age
        self.subject = subject

    def introduce(self):
        parent_introduction = super().introduce() # Call the parent class's introduce
        return f"{parent_introduction} I teach {self.subject}."

class Administrator(Employee):
    def __init__(self, name, age, department):
        super().__init__(name, age, employee_id=None) # Call the parent class's __init__ method to initialize name and age
        self.department = department

    def introduce(self):
        parent_introduction = super().introduce() # Call the parent class's introduce
        return f"{parent_introduction} I work in the {self.department} department."
    
class SchoolMember(Student, Teacher, Administrator):
    def __init__(self, name, age, student_id=None, subject=None, department=None):
        Student.__init__(self, name, age, student_id) # Initialize Student attributes
        Teacher.__init__(self, name, age, subject) # Initialize Teacher attributes
        Administrator.__init__(self, name, age, department) # Initialize Administrator attributes

    def introduce(self):
        student_introduction = Student.introduce(self) # Call the Student's introduce method
        teacher_introduction = Teacher.introduce(self) # Call the Teacher's introduce method
        administrator_introduction = Administrator.introduce(self) # Call the Administrator's introduce method
        return f"{student_introduction} {teacher_introduction} {administrator_introduction}"