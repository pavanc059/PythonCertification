# Example 01
def greet(name: str) -> str:
    return "Hello, " + name

# Example 02
def headline(text, align=True):
    if align:
        return f"{text.title()}\n{'-' * len(text)}"
    else:
        return f" {text.title()} ".center(50, "o")


print(headline("python type checking))

print(headline("python type checking", align=False))

# Example 03
def headline(text: str, align: bool = True) -> str:
    if align:
        return f"{text.title()}\n{'-' * len(text)}"
    else:
        return f" {text.title()} ".center(50, "o")

headline

print(headline("python type checking, align="left"))

print(headline("python type checking, align="center"))
