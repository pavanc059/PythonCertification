input_string1 = input("Enter the first string: ")
input_string2 = input("Enter the second string: ")

input_string1 = input_string1.replace(" ", "")
input_string2 = input_string2.replace(" ", "")

if (len(input_string1) == 0 or len(input_string2) == 0) and len(input_string1) != len(input_string2):
    print("Not anagrams")

'''
Method 1
if sorted(input_string1.lower()) == sorted(input_string2.lower()):
    print("Anagrams")
else:
    print("Not anagrams")
'''

for char in input_string1.lower():
    if char not in input_string2.lower():
        print("Not anagrams")
        break
else:
    print("Anagrams")
