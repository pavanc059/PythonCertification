# vehicle.py

class Vehicle:
    @classmethod
    def water_vehicle(cls, name, dimensions):
        vehicle = Vehicle()
        vehicle.name = name
        vehicle.dimensions = dimensions
        vehicle.floats = True
        vehicle.num_wheels = 0
        return vehicle

    @classmethod
    def road_vehicle(cls, name, dimensions, num_wheels):
        vehicle = Vehicle()
        vehicle.name = name
        vehicle.dimensions = dimensions
        vehicle.floats = False
        vehicle.num_wheels = num_wheels
        return vehicle

    def volume(self):
        return self.dimensions[0] * self.dimensions[1] * self.dimensions[2]

    @staticmethod
    def all_float(*vehicles):
        for vehicle in vehicles:
            if not vehicle.floats:
                return False

        return True
