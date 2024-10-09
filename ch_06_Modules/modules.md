### importing module: 

- import moduleName: will import module specified access any entities using module name and entity name 
- from moduleName import entities : will import specified entity with comma sperated list from given modules
- from modulesName import entityname as aliasname :  this will import specified entity from a module and use differet name using as
- dir() : will give you list of entities in a module but module has to be fully imported will not work using `from math import *` dir(math) will throw error

#### Random module
The seed() function is able to directly set the generator's seed. We'll show you two of its variants:

    seed() - sets the seed with the current time;
    seed(int_value) - sets the seed with the integer value int_value.
If you want integer random values, one of the following functions would fit better:

    randrange(end)
    randrange(beg, end)
    randrange(beg, end, step)
    randint(left, right)

The first three invocations will generate an integer taken (pseudorandomly) from the range (respectively):

    range(end)
    range(beg, end)
    range(beg, end, step)

Note the implicit right-sided exclusion!

The last function is an equivalent of randrange(left, right+1) - it generates the integer value i, which falls in the range [left, right] (no exclusion on the right side).

It's a function named in a very suggestive way - choice:

    choice(sequence)
    sample(sequence, elements_to_choose=1)

The first variant chooses a "random" element from the input sequence and returns it.

The second one builds a list (a sample) consisting of the elements_to_choose element (which defaults to 1) "drawn" from the input sequence.

In other words, the function chooses some of the input elements, returning a list with the choice. The elements in the sample are placed in random order. Note: the elements_to_choose must not be greater than the length of the input sequence.

### platform module
The platform module lets you access the underlying platform's data, i.e., hardware, operating system, and interpreter version information.

There is a function that can show you all the underlying layers in one glance, named platform, too. It just returns a string describing the environment; thus, its output is rather addressed to humans than to automated processing