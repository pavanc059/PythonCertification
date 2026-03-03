# Example 01
if False:
    1 + "two"  # This line never runs, so no TypeError is raised
else:
    1 + 2

# Example 02
1 + "two"  # Now this is type checked

# Example 03
thing = "Hello"
type(thing)

thing = 28.1
type(thing)
