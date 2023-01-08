from dataclasses import dataclass
import re
import sys


class Instruction:
    pass


class InstructionBlock:
    def __init__(self, instructions: list[Instruction] | None = None):
        self.instructions = instructions or []

    def add_instruction(self, instruction: Instruction):
        self.instructions.append(instruction)


@dataclass
class Primary:
    value: str


@dataclass
class TermList:
    op: str
    term: "Term"


@dataclass
class Term:
    primary: "Primary"
    t_list: TermList


@dataclass
class ExpressionList:
    op: str
    expression: "Expression"


@dataclass
class Expression:
    term: Term
    e_list: ExpressionList


@dataclass
class Operation(Instruction):
    idn: str


@dataclass
class AssignOperation(Operation):
    expression: Expression


@dataclass
class ForLoopOperation(Operation):
    range_from: Expression
    range_to: Expression
    block: InstructionBlock


class AST_parser:
    class Line:
        value: str
        indent: int

        def __init__(self, line):
            self.value = line.strip()
            self.indent = len(line) - len(self.value)

        def type(self):
            if re.match(r"^<.*>$", self.value):
                return "tag"
            elif self.value.startswith('IDN'):
                return "idn"
            elif self.value.startswith('OP_'):
                return "op"
            elif self.value.startswith('BROJ'):
                return "num"
            return "unknown"

        def __repr__(self) -> str:
            return f"[{self.indent:2}]{self.value}"

    def __init__(self, lines: list[str]):
        self.lines = [self.Line(line) for line in lines]
        self.index = 0
        self.pointer = None

        while self.index < len(self.lines):
            line = self.lines[self.index]

            match(line.type):
                case "num":
                    pass

            self.index += 1

        self.tree = {}

    def parse(self):
        return self.tree


class FRISCGenerator:
    def __init__(self, input):
        self.input = input
        self.lines = input.splitlines()

    def run(self, output_to_file=True):
        parser = AST_parser(self.lines)
        tree = parser.parse()

        print(tree)


if __name__ == '__main__':
    FRISCGenerator(sys.stdin.read()).run(output_to_file=False)
