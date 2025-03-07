'''
Pay attention to the fact that thanks to polymorphism and explicit chaining, our approach has become more generic: we are able to run two different checks, each returning a different exception type.

And we’re still able to handle them correctly, as we’re hiding some details behind the RocketNotReadyError exception object.
'''
class RocketNotReadyError(Exception):
    pass


def personnel_check():
    try:
        print("\tThe captain's name is", crew[0])
        print("\tThe pilot's name is", crew[1])
        print("\tThe mechanic's name is", crew[2])
        print("\tThe navigator's name is", crew[3])
    except IndexError as e:
        raise RocketNotReadyError('Crew is incomplete') from e


def fuel_check():
    try:
        print('Fuel tank is full in {}%'.format(100 / 0))
    except ZeroDivisionError as e:
        raise RocketNotReadyError('Problem with fuel gauge') from e


crew = ['John', 'Mary', 'Mike']
fuel = 100
check_list = [personnel_check, fuel_check]

print('Final check procedure')

for check in check_list:
    try:
        check()
    except RocketNotReadyError as f:
        print('RocketNotReady exception: "{}", caused by "{}"'.format(f, f.__cause__))


# The output of the code will be:
# Final check procedure

# 	The captain's name is John

# 	The pilot's name is Mary

# 	The mechanic's name is Mike

# RocketNotReady exception: "Crew is incomplete", caused by "list index out of range"

# RocketNotReady exception: "Problem with fuel gauge", caused by "division by zero"
