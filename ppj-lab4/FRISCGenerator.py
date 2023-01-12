from ctypes import cast
import re
import sys
from typing import Literal, Optional
from dataclasses import dataclass


class IllegalStateError(Exception):
    pass


class Instruction:
    def __init__(self):
        raise NotImplementedError


@dataclass
class InstructionBlock:
    instruction: Instruction  # todo make this flatter
    block: Optional["InstructionBlock"]

    @staticmethod
    def parse(lines: list["Line"]) -> "InstructionBlock | None":
        if len(lines) == 1:
            if lines[0].type() != 'non':
                raise IllegalStateError

            return None

        sub = Line.get_subtree(lines[0:])
        instruction = None

        match(lines[1].value):
            case '<naredba_pridruzivanja>':
                instruction = AssignOperation(
                    lines[2].get_part(2),
                    Expression.parse(sub[4:])
                )

        if instruction is None:
            raise NotImplementedError

        return InstructionBlock(instruction, InstructionBlock.parse(lines[len(sub) + 2:]))


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
            return "ope"
        elif self.value.startswith('BROJ'):
            return "num"
        elif self.value == '$':
            return 'non'

        return "__unknown__"

    def get_part(self, index: int):
        return self.value.split(' ')[index]

    def __str__(self) -> str:
        return f"[{self.indent:2}][{self.type()}] {self.value}"

    @staticmethod
    def get_subtree(lines: list["Line"]) -> list["Line"]:
        first_index = lines[0].indent
        arr = []
        for line in lines[1:]:
            if line.indent <= first_index:
                break
            arr.append(line)

        return arr


@dataclass
class Primary:
    value: str
    type: Literal["idn", "num"]

    @staticmethod
    def parse(line: Line) -> "Primary":
        p_type = line.get_part(0).lower()
        if p_type not in ["idn", "broj"]:
            raise IllegalStateError(f"Invalid primary type: {p_type}")

        return Primary(line.get_part(2), p_type)  # type: ignore


@ dataclass
class TermList:
    op: str
    term: "Term"

    @staticmethod
    def parse(lines: list[Line]) -> Optional["TermList"]:
        if len(lines) <= 2:
            return None

        raise NotImplementedError


@ dataclass
class Term:
    primary: "Primary"
    t_list: TermList | None

    @staticmethod
    def parse(lines: list[Line]) -> "Term":
        print('term')
        for line in lines:
            print(line)

        return Term(
            Primary.parse(lines[1]),
            TermList.parse(lines[2:]) if len(lines) > 2 else None
        )


@ dataclass
class ExpressionList:
    op: str
    expression: "Expression"

    @staticmethod
    def parse(lines: list[Line]) -> Optional["ExpressionList"]:
        print('here')
        for l in lines:
            print(l)
        raise NotImplementedError


@ dataclass
class Expression:
    term: Term
    e_list: ExpressionList | None

    @staticmethod
    def parse(lines: list[Line]) -> "Expression":
        t_section = Line.get_subtree(lines[0:])
        t = Term.parse(t_section)

        e_list_index = len(t_section)
        if e_list_index + 1 >= len(lines):
            return Expression(t, None)

        return Expression(t, ExpressionList.parse(lines[e_list_index + 1:]))


@ dataclass
class Operation(Instruction):
    idn: str

    def __init__(self):
        raise NotImplementedError


@ dataclass
class AssignOperation(Operation):
    expression: Expression


@ dataclass
class ForLoopOperation(Operation):
    range_from: Expression
    range_to: Expression
    block: InstructionBlock


class FRISC_generator:
    def __init__(self, input):
        self.input = input
        self.raw_lines = input.splitlines()
        self.lines = [Line(line) for line in self.raw_lines]

    def run(self, output_to_file=True):
        if len(self.lines) <= 2:
            raise IllegalStateError("Invalid input")

        root = InstructionBlock.parse(self.lines[2:])

        print(root)


if __name__ == '__main__':
    FRISC_generator(sys.stdin.read()).run(output_to_file=False)
