from contextlib import redirect_stdout
from io import StringIO
import os

from SintaksniAnalizator import SyntaxAnalyzer


def load_file(filename):
    with open(filename, 'r') as f:
        return f.read()


def load_test(test):
    input_string = load_file(os.path.join('./tests', test, 'test.in'))
    expected_output = load_file(os.path.join('./tests', test, 'test.out'))

    return input_string, expected_output


class MyStringIO(StringIO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output = ''

    def write(self, s):
        self.output += s


if __name__ == '__main__':
    tests = sorted(os.listdir('./tests'))
    # tests = ['31_gen']
    score = 0

    for test in tests:
        input_string, expected_output = load_test(test)

        io = MyStringIO()
        try:
            with redirect_stdout(io):
                SyntaxAnalyzer(input_string).run()
        except Exception as e:
            print(f"Run: ./tests/{test}/test.out failed")
            continue

        with open(os.path.join('./tests', test, 'test.actual'), 'w') as f:
            f.write(io.output)
        os.remove(os.path.join('./tests', test, 'test.actual'))

        if io.output == expected_output:
            score += 1
        else:
            msg = f"Test: ./tests/{test}/test.out failed, output was './tests/{test}/test.actual"
            print(msg)

            # with open(os.path.join('./tests', test, 'test.actual'), 'w') as f:
            #     f.write(io.output)

    print(f'Score: {score}/{len(tests)}')
