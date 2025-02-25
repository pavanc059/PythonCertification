class Scanner:
    def __init__(self):
        pass

    def scan(self):
        print("scan() from Scanner class")

class Printer:
    def __init__(self):
        pass

    def print(self):
        print('print() from Printer class')

class Fax:
    def __init__(self):
        pass

    def send(self):
        print('send() from Fax class')

    def print(self):
        print('print() from Fax class')

class MFD_SPF(Scanner, Printer, Fax):
    def __init__(self):
        pass

class MFD_SFP(Scanner, Fax, Printer):
    def __init__(self):
        pass

mfd_spf = MFD_SPF()
mfd_sfp = MFD_SFP()

mfd_spf.scan()
mfd_spf.print()
mfd_spf.send()


mfd_sfp.scan()
mfd_sfp.print()
mfd_sfp.send()

'''
Output:
scan() from Scanner class

print() from Printer class

send() from Fax class

scan() from Scanner class

print() from Fax class

send() from Fax class
'''