import unittest
import sys
import os
import random

# getting the name of the directory
# where the this file is present.
current = os.path.dirname(os.path.realpath(__file__))

# Getting the parent directory name
# where the current directory is present.
parent = os.path.dirname(current)

# adding the parent directory to 
# the sys.path.
sys.path.append(parent)

from PythonProjects.stringoperations import validationUtilities

class TestStringMethods(unittest.TestCase):

    def test_upper(self):
        self.assertEqual('foo'.upper(), 'FOO')

    def test_isupper(self):
        self.assertTrue('FOO'.isupper())
        self.assertFalse('Foo'.isupper())

    def test_split(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        with self.assertRaises(TypeError):
            s.split(2)

    def test_findGivenStringisASCII(self):
        self.assertEqual(validationUtilities.findGivenStringisASCII("test", True), True)
        self.assertEqual(validationUtilities.findGivenStringisASCII("test", False), False)

if __name__ == '__main__':
    unittest.main()

   

