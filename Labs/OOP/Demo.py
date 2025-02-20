class Demo:
    class_var = "shared_variable"

d1 = Demo()
d2 = Demo()
print(d1.class_var)
#shared_variable
print(Demo.class_var)
#shared_variable
d1.class_var = 'shadowing calss variable'
print(d1.class_var)
#shadowing calss variable