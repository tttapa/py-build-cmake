from .add_module import add
import sys

def main():
    """Script that adds all command line arguments as integers."""
    sum = 0
    for el in sys.argv[1:]:
        sum = add(sum, int(el))
    print(sum)
    return 0
