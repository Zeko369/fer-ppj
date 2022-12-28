import sys


class SemanticAnalyzer:
    def __init__(self, input):
        self.input = input
        self.index = 0
        self.current = input[self.index]
        self.stack = []

    def run(self):
        pass


if __name__ == '__main__':
    SemanticAnalyzer(sys.stdin.read()).run()
