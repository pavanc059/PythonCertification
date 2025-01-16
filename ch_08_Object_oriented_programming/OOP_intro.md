## Class
- A class is like a recipe which can be used when you want to create a useful object (this is where the name of the approach comes from). You may produce as many objects as you  need to solve your problem.
- Every object has a set of traits (they are called properties or attributes - we'll use both words synonymously) and is able to perform a set of activities (which are called methods).

### What is an object?
- A class (among other definitions) is a set of objects. An object is a being belonging to a class.

- An object is an incarnation of the requirements, traits, and qualities assigned to a specific class. This may sound simple, but note the following important circumstances. Classes form a hierarchy. This may mean that an object belonging to a specific class belongs to all the superclasses at the same time. It may also mean that any object belonging to a superclass may not belong to any of its subclasses.

#### What does an object have?
 The object programming convention assumes that every existing object may be equipped with three groups of attributes:
 - An object has a name that uniquely identifies it within its home namespace (although there may be some anonymous objects, too)
 - An object has a set of individual properties which make it original, unique or outstanding (although it's possible that some objects may have no properties at all)
 - An object has a set of abilities to perform specific activities, able to change the object itself, or some of the other objects.

##### Creating a class :
 - Object programming is the art of defining and expanding classes. A class is a model of a very specific part of reality, reflecting properties and activities found in the real world.
 - There's no obstacle to defining new, more precise subclasses. They'll inherit everything from their superclass, so the work that went into its creation isn't wasted.
 - The new class may add new properties and new activities, and therefore may be more useful in specific applications. Obviously, it may be used as a superclass for any number of newly created subclasses.
 - The class you define has nothing to do with the object: the existence of a class does not mean that any of the compatible objects will automatically be created. The class itself isn't able to create an object - you have to create it yourself, and Python allows you to do this.
 - It's time to define the simplest class and to create an object. Take a look at the example below:
    ```
    class TheSimplestClass:
        pass
    ```

##### Creating an Object :
 - The newly defined class becomes a tool that is able to create new objects. The tool has to be used explicitly, on demand.
 - To create a object, you need to assign a variable to store the newly created object of that class, and create an object at the same time.
 ```
 myFirstObject = TheSimplestClass()
 ```
 - The newly created object is equipped with everything the class brings; as this class is completely empty, the object is empty, too.
 - The act of creating an object of the selected class is also called an instantiation (as the object becomes an instance of the class).
