## Stack
- A stack is a structure developed to store data in a very specific way. Imagine a stack of coins. You aren't able to put a coin anywhere else but on the top of the stack. Similarly, you can't get a coin off the stack from any place other than the top of the stack. If you want to get the coin that lies on the bottom, you have to remove all the coins from the higher levels.

- The alternative name for a stack (but only in IT terminology) is LIFO. It's an abbreviation for a very clear description of the stack's behavior: Last In - First Out. The coin that came last onto the stack will leave first.

- A stack is an object with two elementary operations, conventionally named push (when a new element is put on the top) and pop (when an existing element is taken away from the top).

- Stacks are used very often in many classical algorithms, and it's hard to imagine the implementation of many widely used tools without the use of stacks.

### Implementing stack in object oriented way :
- Let's start from the absolute beginning - this is how the objective stack begins:
 ```
 class Stack:
 ```
Now, we expect two things from it:

- we want the class to have one property as the stack's storage - we have to "install" a list inside each object of the class (note: each object has to have its own list - the list mustn't be shared among different stacks) then, we want the list to be hidden from the class users' sight.
- Instead, you need to add a specific statement or instruction. The properties have to be added to the class manually.How do you guarantee that such an activity takes place every time the new stack is created?
- There is a simple way to do it - you have to equip the class with a specific function - its specificity is dual:
  - it has to be named in a strict way;
  - it is invoked implicitly, when the new object is created.
- Such a function is called a constructor, as its general purpose is to construct a new object. The constructor should know everything about the object's structure, and must perform all the needed initializations.
```
class Stack:
    def __init__(self):
        print("Hi!")
```
- The constructor's name is always __init__;
- It has to have at least one parameter (we'll discuss this later); the parameter is used to represent the newly created object - you can use the parameter to manipulate the object, and to enrich it with the needed properties; you'll make use of this soon;

###### note: the obligatory parameter is usually named self - it's only a convention, but you should follow it - it simplifies the process of reading and understanding your code.

#### Adding properties to ojbect through constructor :
```
class Stack:
    def __init__(self):
        self.stackList = []

stackObject = Stack()
print(len(stackObject.stackList))
```
- we've used the dotted notation, just like when invoking methods; this is the general convention for accessing an object's properties - you need to name the object, put a dot (.)after it, and specify the desired property's name; don't use parentheses! You don't want to invoke a method - you want to access a property;
- if you set a property's value for the very first time (like in the constructor), you are creating it; from that moment on, the object has got the property and is ready to use its value;
- we've done something more in the code - we've tried to access the stackList property from outside the class immediately after the object has been created; we want to check the current length of the stack - have we succeeded?
- When any class component has a name starting with two underscores (__), it becomes private - this means that it can be accessed only from within the class.
- You cannot see it from the outside world. This is how Python implements the encapsulation concept.

#### Defining a subclass :
- The first step is easy: just define a new subclass pointing to the class which will be used as the superclass.
```
class AddingStack(Stack):
    pass
```
- The class doesn't define any new component yet, but that doesn't mean that it's empty. It gets all the components defined by its superclass - the name of the superclass is written after the colon directly after the new class name.
- Python forces you to explicitly invoke a superclass's constructor. Omitting this point will have harmful effects - the object will be deprived of the __stackList list. Such a stack will not function properly.
- This is the only time you can invoke any of the available constructors explicitly - it can be done inside the superclass's constructor.

Note the syntax:

    - you specify the superclass's name (this is the class whose constructor you want to run)
    - you put a dot (.)after it;
    - you specify the name of the constructor;
     - you have to point to the object (the class's instance) which has to be initialized by the constructor - this is why you have to specify the argument and use the self variable here; note: invoking any method (including constructors) from outside the class never requires you to put the self argument at the argument's list - invoking a method from within the class demands explicit usage of the self argument, and it has to be put first on the list.

```
class AddingStack(Stack):
    def __init__(self):
        Stack.__init__(self)
        self.__sum = 0
```



