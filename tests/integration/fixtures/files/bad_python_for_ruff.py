# This file has intentional lint issues for testing ruff


def bad_function():
    x = 1
    y = 2
    print(x + y)
    unused_var = 'this will trigger ruff warnings'


class BadClass:
    def __init__(self, x, y):
        self.x = x
        self.y = y


def another_bad_function():
    pass
