# point.py

import math

class PolarPoint:
    def __init__(self, distance, angle):
        self.distance = distance
        self.angle = angle

    @classmethod
    def from_cartesian(cls, x, y):
        distance = math.dist((0, 0), (x, y))
        angle = math.degrees(math.atan2(y, x))
        return cls(distance, angle)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"(distance={self.distance:.1f},angle={self.angle:.1f})"
        )
