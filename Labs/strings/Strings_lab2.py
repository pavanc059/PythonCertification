listString = []

listString.append("#### ## ## ####")
listString.append("  #  #  #  #  #")
listString.append("###  #####  ###")
listString.append("###  ####  ####")
listString.append("# ## ####  #  #")
listString.append("####  ###  ####")
listString.append("####  #### ####")
listString.append("###  #  #  #  #")
listString.append("#### ##### ####")
listString.append("#### ####  ####")

input_text = input("Enter a number: ")
output_text = []
if not input_text.isnumeric:
    print("Invalid number")

start = 0
for line in range(5):
    print_value = ""    
    for i, value in enumerate(input_text):      
        print_value += listString[int(value)][start:start+3]

        print_value = print_value +" "
    print(print_value)
    start += 3