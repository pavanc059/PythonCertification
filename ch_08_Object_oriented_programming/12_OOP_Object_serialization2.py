import pickle

with open('function.pckl', 'rb') as file_in:
    data = pickle.load(file_in)
    
print(data)

'''
Traceback (most recent call last):
  File "12_OOP_Object_serialization2.py", line 4, in <module>
    data = pickle.load(file_in)
           ^^^^^^^^^^^^^^^^^^^^
AttributeError: Can't get attribute 'f1' on <module '__main__' from '12_OOP_Object_serialization2.py'>
'''