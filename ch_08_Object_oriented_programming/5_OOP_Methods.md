# Methods in Python

## Introduction
Methods in Python are functions that are associated with an object. They are defined within a class and are used to perform operations on the data contained within the object.

## Defining Methods
To define a method in a class, you use the `def` keyword, followed by the method name and parentheses. The first parameter of a method is always `self`, which refers to the instance of the class.

```python
class MyClass:
    def my_method(self):
        print("Hello, World!")
```

## Calling Methods
To call a method, you need to create an instance of the class and then use the dot notation to call the method.

```python
obj = MyClass()
obj.my_method()  # Output: Hello, World!
```

## Types of Methods
There are three types of methods in Python:

1. **Instance Methods**: These are the most common type of methods. They take `self` as the first parameter and can access and modify the object's attributes.
    -   The instance methods, as the first parameter, take the self parameter, which is their hallmark. It’s worth emphasizing and remembering that self allows you to refer to the instance. Of course, it follows that in order to successfully use the instance method, the instance must have previously existed.
    -   The name of the parameter self was chosen arbitrarily and you can use a different word, but you must do it consistently in your code. It follows from the convention that self literally means a reference to the instance. 

2. **Class Methods**: These methods take `cls` as the first parameter and can access and modify the class state. They are defined using the `@classmethod` decorator.
    -   Class methods are methods that, like class variables, work on the class itself, and not on the class objects that are instantiated. You can say that they are methods bound to the class, not to the object.
    -   When can this be useful? 
        -   we control access to class variables, e.g., to a class variable containing information about the number of created instances or the serial number given to the last produced object, or we modify the state of the class variables;
        -   we need to create a class instance in an alternative way, so the class method can be implemented by an alternative constructor.
    - Convention :
      - To be able to distinguish a class method from an instance method, the programmer signals it with the @classmethod decorator preceding the class method definition. 
      - Additionally, the first parameter of the class method is cls, which is used to refer to the class methods and class attributes.
  
  `As with self, cls was chosen arbitrarily (i.e., you can use a different name, but you must do it consistently).`

    ```python
    class MyClass:
        class_variable = 0

        @classmethod
        def class_method(cls):
            cls.class_variable += 1
    ```
   Alternative constructor:

   ```python
   class Car:
    def __init__(self, vin):
        print('Ordinary __init__ was called for', vin)
        self.vin = vin
        self.brand = ''

    @classmethod
    def including_brand(cls, vin, brand):
        print('Class method was called')
        _car = cls(vin)
        _car.brand = brand
        return _car

    car1 = Car('ABCD1234')
    car2 = Car.including_brand('DEF567', 'NewBrand')

    print(car1.vin, car1.brand)
    print(car2.vin, car2.brand)
    #output 
    #Ordinary __init__ was called for ABCD1234
    #Class method was called
    #Ordinary __init__ was called for DEF567
  #ABCD1234 
  #DEF567 NewBrand
   ```

1. **Static Methods**: These methods do not take `self` or `cls` as the first parameter. They are defined using the `@staticmethod` decorator and cannot modify the object or class state.
    - When you need a utility method that comes in a class because it is semantically related, but does not require an object of that class to execute its code;
    - consequently, when the static method does not need to know the state of the objects or classes.

    ```python
    class MyClass:
        @staticmethod
        def static_method():
            print("This is a static method.")
    ```
#### An example of using the static method
```python
class Bank_Account:
    def __init__(self, iban):
        print('__init__ called')
        self.iban = iban
            
    @staticmethod
    def validate(iban):
        if len(iban) == 20:
            return True
        else:
            return False


account_numbers = ['8' * 20, '7' * 4, '2222']

for element in account_numbers:
    if Bank_Account.validate(element):
        print('We can use', element, ' to create a bank account')
    else:
        print('The account number', element, 'is invalid')

```

This is a great place to introduce a static method, which, provided by the bank account class, will be used to validate the character string and will answer the question: can a given character string be an account number before the object is created?

To shorten the size of the sample code, the static method responsible for validation checks only the length of the string, and only those numbers whose length is 20 characters are treated as valid. 

## Using static and class methods - comparison
1) a class method requires 'cls' as the first parameter and a static method does not;
2) a class method has the ability to access the state or methods of the class, and a static method does not;
3) a class method is decorated by '@classmethod' and a static method by '@staticmethod';
4) a class method can be used as an alternative way to create objects, and a static method is only a utility method. 

## Conclusion
Methods are an essential part of object-oriented programming in Python. They allow you to define the behavior of objects and interact with their data. Understanding the different types of methods and how to use them is crucial for writing effective Python code.