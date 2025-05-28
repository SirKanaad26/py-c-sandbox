# main.py
from capitalize_wrapper import py_capitalize

if __name__ == "__main__":
    s = "hello, world!"
    print("Original:", s)
    print("Capitalized:", py_capitalize(s))
