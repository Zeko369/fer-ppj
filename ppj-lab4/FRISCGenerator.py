import sys


class FRISCGenerator:
    def __init__(self, input):
        self.input = input
        self.lines = input.splitlines()

    def run(self, output_to_file=True):
        print(self.lines)


if __name__ == '__main__':
    FRISCGenerator(sys.stdin.read()).run(output_to_file=False)
