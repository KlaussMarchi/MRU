import sys

def sign(x):
    return 1 if x > 0 else -1 if x < 0 else 0

def println(text):
    sys.stdout.write(f'{text}\n')
