class Mobile:
    def __init__(self, number):
        self.number = number
        

    def turn_on(self):
        return print(f'mobile phone {self.number} is turned on')

    def turn_off(self):
        return print(f'mobile phone {self.number} is turned off')

    def call(self,number):
        return print(f'calling {number}')
        

phone1 = Mobile('4696577578')
phone2 = Mobile('3434342243')

phone1.turn_on()
phone2.turn_on()
phone1.call('85413212646')
phone1.turn_off()
phone2.turn_off()
