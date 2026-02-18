# person.py

from datetime import date
from functools import singledispatchmethod

class BirthInfo:
    @singledispatchmethod
    def __init__(self, birth_date):
        raise ValueError(f"unsupported date format: {birth_date}")

    @__init__.register(date)
    def _from_date(self, birth_date):
        self.date = birth_date

    @__init__.register(str)
    def _from_isoformat(self, birth_date):
        self.date = date.fromisoformat(birth_date)

    @__init__.register(int)
    @__init__.register(float)
    def _from_timestamp(self, birth_date):
        self.date = date.fromtimestamp(birth_date)

    def age(self):
        return date.today().year - self.date.year

class Person:
    def __init__(self, name, birth_date):
        self.name = name
        self._birth_info = BirthInfo(birth_date)

    @property
    def age(self):
        return self._birth_info.age()

    @property
    def birth_date(self):
        return self._birth_info.date
