number_list = [1, 0, 'p', [10, 7], 8]
try:
    for x in number_list:
        x /= x
        print(f'x value is {x}')
except:
    print("Error")
