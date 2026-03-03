# headlines.py

def headline1(text, width=80, fill_char="-"):
    # type: (str, int, str) -> str
    return f" {text.title()} ".center(width, fill_char)

print(headline1("type comments work", width=40))

def headline2(
    text,           # type: str
    width=80,       # type: int
    fill_char='-',  # type: str
):                  # type: (...) -> str
    return f" {text.title()} ".center(width, fill_char)

print(headline2("these type comments also work", width=70))

pi = 3.142  # type: float