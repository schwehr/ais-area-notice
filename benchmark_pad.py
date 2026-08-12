import timeit

setup = """
string = "HELLO"
length = 20

def pad_old(string: str, length: int) -> str:
    pad_len = length - len(string)
    if pad_len > 0:
        string += "@" * pad_len
    return string

def pad_new(string: str, length: int) -> str:
    return string.ljust(length, "@")
"""

print("Old pad:", timeit.timeit("pad_old(string, length)", setup=setup, number=1000000))
print("New pad:", timeit.timeit("pad_new(string, length)", setup=setup, number=1000000))
