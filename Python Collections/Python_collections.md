## Python Collections

* **[list :](https://docs.python.org/3/tutorial/datastructures.html "Datastructures")** list is a collection of elements, but each element is a scalar. list starts with an open square bracket and ends with a closed square bracket. Python has adopted a convention stating that the elements in a list are always numbered starting from zero. This means that the item stored at the beginning of the list will have the number zero.

  - The value inside the brackets which selects one element of the list is called an  **index** , while the operation of selecting an element from the list is known as  **indexing** .
  - If you want to check the list's current length, you can use a function named `len()` (its name comes from  *length* )
  - Any of the list's elements may be **removed** at any time - this is done with an instruction named `del` (delete). Note: it's an  **instruction** , not a function. `del` `numbers[1]`
  - It may look strange, but negative indices are legal, and can be very useful. i.e : `numbers[-1]`

  ```
  Example of list :
  number_list = [1,0,'p', [10,7],8]
  ```

  - List methods :

    - append() - A new element may be glued to the end of the existing list. It takes its argument's value and puts it at the end of the list which owns the method.
    - insert() method is a bit smarter - it can add a new element at any place in the list, not only at the end.It takes two arguments, the first shows the required location of the element to be inserted; note: all the existing elements that occupy locations to the right of the new element (including the one at the indicated position) are shifted to the right, in order to make space for the new element; the second is the element to be inserted.
  - The for instruction specifies the variable used to browse the list (i here) followed by the in keyword and the name of the list being processed.
  - You can use the `sort()` method to sort elements of a list
  - There is also a list method called `reverse()`, which you can use to reverse the list.
  - The name of an ordinary variable is the **name of its content. The name of a list is the name of a memory location where the list is stored.**

    ```
    Code Example :
    list_1 = [1]
    list_2 = list_1
    list_1[0] = 2
    print(list_2)

    The assignment: list_2 = list_1 copies the name of the array, not its contents. In effect, the two names (list_1 and list_2) identify the same location in the computer memory. Modifying one of them affects the other, and vice versa.
    ```

  # Functions vs. methods

  A **method is a specific kind of function** - it behaves like a function and looks like a function, but differs in the way in which it acts, and in its invocation style.

  A **function doesn't belong to any data** - it gets data, it may create new data and it (generally) produces a result.

  A method does all these things, but is also able to  **change the state of a selected entity** .

  **A method is owned by the data it works for, while a function is owned by the whole code** .

exmpale : `result = function(arg) and result = data.method(arg)`
