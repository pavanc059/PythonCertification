'''Objectives - Pending pavan

Familiarize the student with:

    projecting and writing parameterized functions;
    utilizing the return statement;
    utilizing the student's own functions.

Scenario

Your task is to write and test a function which takes two arguments (a year and a month) and returns the number of days for the given month/year pair (while only February is sensitive to the year value, your function should be universal).

The initial part of the function is ready. Now, convince the function to return None if its arguments don't make sense.

Of course, you can (and should) use the previously written and tested function (LAB 4.3.1.6). It may be very helpful. We encourage you to use a list filled with the months' lengths. You can create it inside the function - this trick will significantly shorten the code.

We've prepared a testing code. Expand it to include more test cases.

Your task is to write and test a function which takes three arguments (a year, a month, and a day of the month) and returns the corresponding day of the year, or returns None if any of the arguments is invalid.

Use the previously written and tested functions. Add some test cases to the code. This test is only a beginning.

'''


def is_year_leap(year):
    if year % 4 == 0:
        if year % 100 == 0:
            if year % 400 == 0:
                return True
            else:
                return False
        else:
            return True
    else:
        return False


def days_in_month(year, month):
    if month == 2:
        if is_year_leap(year):
            return 29
        else:
            return 28
    elif month > 7:
        if month % 2 == 0:
            return 31
        else:
            return 30
    else:
        if month % 2 == 0:
            return 30
        else:
            return 31


days_of_week = [ 'Tuesday', 'Wednsday', 'Thrusday','Friday', 'Saturday', 'Sunday', 'Monday']

def day_of_year(year, month, day):
    total_days = 0
    for i in range(1,month+1):
        print(days_in_month(year, i))
        total_days += days_in_month(year, i)
    print(total_days)
    day = (total_days + day)%7
    print(day)
    return days_of_week[day]


print(day_of_year(2021, 8, 23))
