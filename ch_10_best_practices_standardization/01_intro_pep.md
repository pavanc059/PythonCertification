# PEP in Python

## What is a PEP?

A Python Enhancement Proposal (PEP) is a design document that provides information to the Python community or describes a new feature for Python. PEPs are the primary mechanism for proposing major new features, collecting community input, and documenting design decisions.


## Importance of PEPs

- **Consistency**: Ensures uniformity in Python code and practices.
- **Documentation**: Serves as a historical record of decisions and changes.
- **Community Collaboration**: Encourages contributions and feedback from the Python community.

## PEP 1 – PEP Purpose and Guidelines
- PEP is an acronym that stands for Python Enhancement Proposals, which, in fact, is a collection of guidelines, best practices, descriptions of (new) features and implementations, as well as processes, mechanisms and important information surrounding Python.
- If a new feature is planned to be added to Python, it will be detailed in a PEP along with the technical specifications and the rationale for its implementation.

#### Types of PEPs

1. **Standards Track PEPs**: Propose new features or implementations for Python.
2. **Informational PEPs**: Provide guidelines or information to the Python community.
3. **Process PEPs**: Describe processes or changes to the Python development process.

#### Last but not least, PEP 1 defines:

- Python’s Steering Council, i.e., a five-person committee and the final authorities who accept or reject PEPs;
- Python’s Core Developers, i.e., the group of volunteers who manage Python, and;
- Python’s BDFL, i.e., Guido van Rossum, the original creator of Python, who served as the project’s Benevolent Dictator For Life until 2018, when he resigned from the decision-making process.


## PEP 20 - THe Zen of Python

The Zen of Python is a collection of 19 aphorisms, which reflect the philosophy behind Python, its guiding principles, and design.

- Tim Peters, a long time major contributor to the Python programming language and Python community, wrote this 19-line poem on the Python mailing list in 1999, and it became entry #20 in the Python Enhancement Proposals in 2004.
- It’s one of the Easter eggs (i.e., hidden, secret messages or features) included in the Python interpreter.

```python
import this
```
1) __Beautiful is better than ugly__ : 
   Even though the computer doesn’t care about beauty or esthetics, people do, and we must remember that a nicely-written program is not only more enjoyable to read, but also more readable.
2) __Explicit is better than implicit__ : 
   The code you write should be explicit and readable. Whenever you want to use an implicit feature of the language, ask yourself whether you really need it. Maybe there’s a better way to implement the functionality. If not, think about leaving a comment in code to explain what’s going on so that other programmers find it easier to understand your code.
3) __Simple is better than complex__ :
   A simpler solution is usually preferred over a complex one, and generally, the minimalistic approach wins. Remember: use appropriate tools adjusted to the specificity of your project.
4) __Complex is better than complicated__ : 
   When simple solutions are not possible, be aware of the limitations carried by simplicity, and use complex solutions instead.Distinguishing between complex as consisting of many elements and complicated, meaning difficult to understand, is yet another thing to consider when writing code.
5) __Flat is better than nested__ :
   Nesting code makes it more difficult to follow and understand. Nesting two or three levels deep may still be good, but anything beyond that becomes confusing and unreadable.
6) __Sparse is better than dense__ : 
   Don’t write too much code in one line, don’t fit too much information into a small amount of code, don’t write lines of code that are too long, use whitespaces responsibly – this all affects the readability and understanding of your program.
7) __Readability counts__ : 
   Your code is not only read by computers, it’s also (or most of all) read by humans. In fact, it’s the essence of the Python philosophy, and the whole of Python design and culture actually revolves around the very statement that “code is read more often than it is written” (Guido Van Rossum). Giving meaningful names to variables, functions, modules, and classes; properly styling blocks of code; using comments where necessary; keeping your code neat and elegant – these all contribute to how readable and user-friendly your code is.
8) __Special cases aren't special enough to break the rules__ : 
   Discipline, consistency, and compliance with standards and conventions are all important elements in professional and responsible code development. There should be no exceptions that allow us to break the principles governing best coding practices.
9)  __Although practicality beats purity__ :
    Well, we must remember that the ultimate goal is to solve real problems and write code that performs some particular (expected) task. If your code is elegant, readable, and complies with all the important styling conventions, but does not function the way it should, then it doesn’t make much sense, does it?
    If the possible benefits (e.g., better performance) are larger than the possible negative effects (e.g., affected maintainability), the real-world coding problems may find an excuse for making an exception to the rules. Practicality then becomes more important than purity.
10) __Errors should never pass silently__ :
    A program that crashes is easier to debug than a program that silences an error. Raising an exception draws your attention to the issue and provides important information about what happened and why. Errors which pass silently may infect the program and change its operation so that it becomes unpredictable, unexpected, and undesired.
    
    One of the most difficult jobs a programmer needs to do is to think of all the possible contexts (or at least as many of them as possible) in which an exception may occur. Serving these exceptions and providing a remedy for expected (and well-handled) errors is an important challenge, but at the same time a crucial responsibility of a good, professional programmer.
11) Unless explicitly silenced.
12) __In the face of ambiguity, refuse the temptation to guess__ :
    Guesses will surely work in many cases, but in many others they may bitterly disappoint you. This guideline conveys a twofold message: on the one hand, it tells you to have limited trust in the code you’re writing, while on the other hand, it implies that you should have limited trust in the code you’re reading. But what does that mean?
    
    Another thing is that you should avoid writing ambiguous code, which means you should leave no room for guessing. Give your variables self-commenting names, and leave comments where necessary. If you’re importing a module, make the import an explicit one. If a particular snippet is complex or complicated, explain its functioning. Never leave comments or use names that are wrong, confusing or misleading!
    
13) __There should be one-- and preferably only one --obvious way to do it__ : 
    The guideline also reminds us that it’s a good idea to follow the language use standards and conventions. For example, if you’ve been using snake_case to name your variables in your code so far, it may be a bad idea to start using CamelCase for the rest of your code within one and the same program. Well, unless you do this for a specific purpose, and the advantages of such an approach are bigger than the disadvantages.
14) Although that way may not be obvious at first unless you're Dutch.
15) __Now is better than never__ :
    You should not put off till tomorrow what you can do today. It’s a well-known proverb. Why? Well, because there’s never a good time for anything – there are always some “buts” and “ifs” which tell you to wait longer and delay things. Before you actually get down to doing these things – writing your code – you may have forgotten the ideas or information you need to do it well.
    
    Python lets you quickly translate your ideas into working code. Whenever you experience the eureka effect or have your moment of inspiration, write down your thoughts and encode them in Python (or at least use some form of pseudocode) – even if your code is far from perfect. You can later refine, develop, or redesign it very easily.
16) Although never is often better than *right* now.
17) __If the implementation is hard to explain, it's a bad idea__ :
    Everything and anything that can be explained in words can be translated into code, and eventually turned into a well-operating computer program.
    If you can explain what you expect from a program, what you want it to do – such a program can be designed. If you find it difficult to explain its features and functionality, it may be a signal that maybe your idea should be thought over again and digested.
18) If the implementation is easy to explain, it may be a good idea.
19) Namespaces are one honking great idea -- let's do more of those!
20) 





## PEP 8

PEP 8 is the style guide for Python code. It provides conventions for writing clean and readable Python code, such as:

- Use 4 spaces per indentation level.
- Limit lines to 79 characters.
- Use meaningful variable names.

For more details, visit the [PEP Index](https://peps.python.org/).
