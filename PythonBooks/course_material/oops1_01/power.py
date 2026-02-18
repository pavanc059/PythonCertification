# power.py

class CumulativePowerFactory:
    def __init__(self, exponent=2, *, start=0):
        self._exponent = exponent
        self.total = start

    def __call__(self, base):
        power = base ** self._exponent
        self.total += power
        return power
