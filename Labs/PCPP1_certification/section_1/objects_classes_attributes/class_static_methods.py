from enum import Enum

class DaysInAWeek(Enum):
    Monday = 0
    Tuesday = 1
    Wednesday = 2
    Thursday = 3
    Friday = 4
    Saturday = 5
    Sunday = 6

class Employee:
    raise_amount = 1.04    

    def __init__(self, first, last, pay):
        self.first = first
        self.last = last
        self.pay = pay

    def fullname(self):
        return f'{self.first} {self.last}'
    
    @classmethod
    def update_raise_amount(cls, amount):
        cls.raise_amount = amount

    @classmethod
    def from_string(cls, emp_str):
        first, last, pay = emp_str.split('-')
        return cls(first, last, int(pay))

    @staticmethod
    def is_workday(day):
        if isinstance(day, int):
            day = DaysInAWeek(day).value
            if day in (5, 6):
                return False
        elif isinstance(day, str):
            if day.capitalize() in DaysInAWeek.__members__:
                day = DaysInAWeek[day.capitalize()].name
            else:
                raise ValueError("Invalid day name")
            if day in (DaysInAWeek.Saturday.name, DaysInAWeek.Sunday.name):
                return False
        else:
            raise TypeError("day must be an integer or a DaysInAWeek enum value")
        
        return True
    
