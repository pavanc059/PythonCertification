# aircraft.py

class AirCraft:
    def __init__(self, make, model):
        self.make = make
        self.model = model
        self._flying = False

    def takeoff(self):
        print("Taking off")
        self._flying = True

    def land(self):
        print("Landing")
        self._flying = False


class Plane(AirCraft):
    def __init__(self, make, model, num_engines):
        super().__init__(make, model)
        self.num_engines = num_engines

    def takeoff(self):
        super().takeoff()
        print("Gear up")

    def land(self):
        super().land()
        print("Gear down")
