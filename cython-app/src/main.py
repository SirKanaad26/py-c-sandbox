# main.py
from capitalize_wrapper import cy_capitalize

if __name__ == "__main__":
    s = "hello, world!"
    print("Original:", s)
    print("Capitalized:", cy_capitalize(s))
