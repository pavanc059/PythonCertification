'''


Having a validateIBAN() function in place, we can write our own class that inherits after a built-in dict class.
class IBANDict(dict):
    def __setitem__(self, _key, _val):
        if validateIBAN(_key):
            super().__setitem__(_key, _val)

    def update(self, *args, **kwargs):
        for _key, _val in dict(*args, **kwargs).items():
            self.__setitem__(_key, _val)



In this implementation, we have delivered the method __setitem__() which calls validateIBAN() and on success calls the genuine __setitem__() method. This piece of code is responsible for statements like:
my_dict[key] = value



We have also delivered the method update() which iterates the parameters passed, and for each correct pair calls the __setitem__() method

After joining all the snippets, we get the following code:

This is a good example of making use of the subclassing feature to enrich your code with an important set of syntax and semantic checks.

To test the efficiency, add and try running the following code:
try:
    my_dict.update({'dummy_account': 100})
except IBANValidationError:
    print('IBANDict has protected your dictionary against incorrect data insertion')



The output should make your eyes happy.
The my_dict dictionary contains:
    GB72 HBZU 7006 7212 1253 00 -> 683
    FR76 30003 03620 00020216907 50 -> 240
    DE02100100100152517108 -> 114
IBANDict has protected your dictionary against incorrect data insertion

output

    Sandbox

Code
import random


class IBANValidationError(Exception):
pass


class IBANDict(dict):
def __setitem__(self, _key, _val):
if validateIBAN(_key):
super().__setitem__(_key, _val)

def update(self, *args, **kwargs):
for _key, _val in dict(*args, **kwargs).items():
self.__setitem__(_key, _val)


def validateIBAN(iban):
iban = iban.replace(' ', '')

if not iban.isalnum():
raise IBANValidationError("You have entered invalid characters.")

elif len(iban) < 15:
raise IBANValidationError("IBAN entered is too short.")

elif len(iban) > 31:
raise IBANValidationError("IBAN entered is too long.")

else:
iban = (iban[4:] + iban[0:4]).upper()
iban2 = ''
for ch in iban:
if ch.isdigit():
iban2 += ch
else:
iban2 += str(10 + ord(ch) - ord('A'))
ibann = int(iban2)

if ibann % 97 != 1:
raise IBANValidationError("IBAN entered is invalid.")

return True


my_dict = IBANDict()
keys = ['GB72 HBZU 7006 7212 1253 00', 'FR76 30003 03620 00020216907 50', 'DE02100100100152517108']

for key in keys:
my_dict[key] = random.randint(0, 1000)

print('The my_dict dictionary contains:')
for key, value in my_dict.items():
print("\t{} -> {}".format(key, value))

try:
my_dict.update({'dummy_account': 100})
except IBANValidationError:
print('IBANDict has protected your dictionary against incorrect data insertion')

    Console


'''
import random


class IBANValidationError(Exception):
    pass


class IBANDict(dict):
    def __setitem__(self, _key, _val):
        if validateIBAN(_key):
            super().__setitem__(_key, _val)

    def update(self, *args, **kwargs):
        for _key, _val in dict(*args, **kwargs).items():
            self.__setitem__(_key, _val)


def validateIBAN(iban):
    iban = iban.replace(' ', '')

    if not iban.isalnum():
        raise IBANValidationError("You have entered invalid characters.")

    elif len(iban) < 15:
        raise IBANValidationError("IBAN entered is too short.")

    elif len(iban) > 31:
        raise IBANValidationError("IBAN entered is too long.")

    else:
        iban = (iban[4:] + iban[0:4]).upper()
        iban2 = ''
        for ch in iban:
            if ch.isdigit():
                iban2 += ch
            else:
                iban2 += str(10 + ord(ch) - ord('A'))
        ibann = int(iban2)

        if ibann % 97 != 1:
            raise IBANValidationError("IBAN entered is invalid.")

        return True


my_dict = IBANDict()
keys = ['GB72 HBZU 7006 7212 1253 00', 'FR76 30003 03620 00020216907 50', 'DE02100100100152517108']

for key in keys:
    my_dict[key] = random.randint(0, 1000)

print('The my_dict dictionary contains:')
for key, value in my_dict.items():
    print("\t{} -> {}".format(key, value))

try:
    my_dict.update({'dummy_account': 100})
except IBANValidationError:
    print('IBANDict has protected your dictionary against incorrect data insertion')
