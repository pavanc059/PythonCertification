'''
In the next example, we’ll create a class based on Python’s built-in dictionary, which will be equipped with logging mechanisms for details of writing and reading operations performed on the elements of our dictionary.

In other words, we are arming a Python dictionary with the ability to log details (time and operation type) of:

    class instantiation;
    read access;
    new element creation or update.

A few notes for the code implementing the MonitoredDict class:

    we have subclassed a dict class with a new __init__() method that calls the __init__() method from its super class. Additionally, it creates a list (self.log) that plays the role of a log book. Finally, the log book is populated with a message noting that the object has been created;
    we have created the log_timestamp() method that appends crucial information to the self.log attribute;
    we have overridden two methods inherent for the dictionary class (__getitem__() and __setitem__()) to deliver a richer implementation that logs activities. But don’t worry, we’re not losing anything from the parent dictionary class, because we’re still calling the corresponding methods.

As you run the code, you'll see that the new class is compatible with its parent, so you can use it in your applications that require activity tracking.

How about implementing such a “history recording” feature in a banking application?

In the following slide, we'll examine another feature that could be useful in a banking app.

'''
from datetime import datetime


class MonitoredDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = list()
        self.log_timestamp('MonitoredDict created')

    def __getitem__(self, key):
        val = super().__getitem__(key)
        self.log_timestamp('value for key [{}] retrieved'.format(key))
        return val

    def __setitem__(self, key, val):
        super().__setitem__(key, val)
        self.log_timestamp('value for key [{}] set'.format(key))

    def log_timestamp(self, message):
        timestampStr = datetime.now().strftime("%Y-%m-%d (%H:%M:%S.%f)")
        self.log.append('{} {}'.format(timestampStr, message))


kk = MonitoredDict()
kk[10] = 15
kk[20] = 5

print('Element kk[10]:', kk[10])
print('Whole dictionary:', kk)
print('Our log book:\n')
print('\n'.join(kk.log))
