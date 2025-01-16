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


