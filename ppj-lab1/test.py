from contextlib import redirect_stdout
from io import StringIO
import os

from LeksickiAnalizator import process


def load_file(filename):
    with open(filename, 'r') as f:
        return f.read()


def load_test(test):
    input_string = load_file(os.path.join('./tests', test, 'test.pj'))
    expected_output = load_file(os.path.join('./tests', test, 'test.in'))

    return input_string, expected_output


class MyStringIO(StringIO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output = ''

    def write(self, s):
        self.output += s


if __name__ == '__main__':
    tests = sorted(os.listdir('./tests'))
    score = 0

    for test in tests:
        input_string, expected_output = load_test(test)

        io = MyStringIO()
        with redirect_stdout(io):
            process(input_string)

        if io.output == expected_output:
            score += 1

    print(f'Score: {score}/{len(tests)}')
