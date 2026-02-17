'''
Write a class Mobile that represents a mobile phone. 
The class should have the following attributes: 
- number (a string representing the phone number)
The class should have the following methods:'''
class Mobile:
    '''A class to represent a mobile phone'''
    def __init__(self, number):
        self.number = number        

    def turn_on(self):
        '''Turn on the mobile phone'''
        return print(f'mobile phone {self.number} is turned on')

    def turn_off(self):
        '''Turn off the mobile phone'''
        return print(f'mobile phone {self.number} is turned off')

    def call(self,number):
        '''Call the number'''
        return print(f'calling {number}')
    
    def __internal_allow_call(self, number):
        '''Internal method to check if the call can be made'''
        return True

phone1 = Mobile('4696577578')
phone2 = Mobile('3434342243')

phone1.turn_on()
phone2.turn_on()
phone1.call('85413212646')
phone1.turn_off()
phone2.turn_off()


