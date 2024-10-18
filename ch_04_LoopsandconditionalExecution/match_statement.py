def http_error(status):
    """
    """
    match status:
        case 400:
            return "Bad request"
        case 404:
            return "Not found"
        case 418:
            return "I'm a teapot"
        case _:
            return "Something's wrong with the internet"
        
#print(http_error(410))

def match_point(point):
    match point:
        case (0, 0):
            print("Origin")
        case (0, y):
            print(f"Y={y}")
        case (x, 0):
            print(f"X={x}")
        case (x, y):
            print(f"X={x}, Y={y}")
        case _:
            raise ValueError("Not a point")
        
#match_point((1,0))

class Point:
    __match_args__ = ('x', 'y')
    def __init__(self, x, y):
        self.x = x
        self.y = y

def where_is(point):
    match point:
        case Point(x=0, y=0):
            print("Origin")
        case Point(x=0, y=y):
            print(f"Y={y}")  
            print(type(point) is Point)      
        case Point(x=x, y=0):
            print(f"X={x}")
        case Point(x=x, y=y):
            print(f"X={x} | Y={y}")        
        case Point():
            print("Somewhere else")
        case _:
            print("Not a point")

point = Point(0,'test')
print(type(point) is Point)
where_is(point)