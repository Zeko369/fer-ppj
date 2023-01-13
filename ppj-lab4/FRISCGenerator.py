import re
import sys
import pprint
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
        sub = Line.get_subtree(lines[0:])
        if len(sub) == 1:
            if sub[0].type() == 'non':
                return None

            raise IllegalStateError

        raw_instruction = Line.get_subtree(sub[0:])
        raw_instruction_block = sub[len(raw_instruction) + 1:]

        return InstructionBlock(
            Operation.parse(raw_instruction),
            InstructionBlock.parse(raw_instruction_block)
        )


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
        term = Line.get_subtree(lines[0:])
        rest = lines[len(term) + 1:]

        return Term(
            Primary.parse(term[0]),
            TermList.parse(rest) if len(rest) > 2 else None
        )


@ dataclass
class ExpressionList:
    op: str
    expression: "Expression"

    @staticmethod
    def parse(lines: list[Line]) -> Optional["ExpressionList"]:
        items = Line.get_subtree(lines[0:])

        return ExpressionList(
            items[0].get_part(0),
            Expression.parse(items[1:])
        )


@ dataclass
class Expression:
    term: Term
    e_list: ExpressionList | None

    @staticmethod
    def parse(lines: list[Line]) -> "Expression":
        t_section = Line.get_subtree(lines[1:])
        t = Term.parse(t_section)

        e_list_index = len(t_section) + 1
        rest = lines[e_list_index + 1:]
        if len(rest) <= 2:
            return Expression(t, None)

        return Expression(t, ExpressionList.parse(rest))


@ dataclass
class Operation(Instruction):
    idn: str

    def __init__(self):
        raise NotImplementedError

    @staticmethod
    def parse(lines: list[Line]) -> "Operation":
        match(lines[0].value):
            case '<naredba_pridruzivanja>':
                assignment = Line.get_subtree(lines)
                return AssignOperation(
                    assignment[0].get_part(2),
                    Expression.parse(assignment[2:])
                )
            case '<za_petlja>':
                raise NotImplementedError
            case _:
                raise NotImplementedError


@ dataclass
class AssignOperation(Operation):
    expression: Expression


@ dataclass
class ForLoopOperation(Operation):
    range_from: Expression
    range_to: Expression
    block: InstructionBlock


class AST_parser:
    def __init__(self, lines: list[str]):
        if len(lines) <= 2:
            raise IllegalStateError("Invalid input")

        self.lines = [Line(line) for line in lines]
        if self.lines[0].value != "<program>":
            raise IllegalStateError("Invalid input")

    def run(self) -> InstructionBlock:
        block = InstructionBlock.parse(self.lines[1:])
        if block is None:
            raise IllegalStateError("Invalid input")

        return block


class FRISC_generator:
    def __init__(self, input):
        self.input = input
        self.raw_lines = input.splitlines()

    def run(self, output_to_file=True):
        parser = AST_parser(self.raw_lines)
        root = parser.run()

        pprint.pprint(root)


if __name__ == '__main__':
    FRISC_generator(sys.stdin.read()).run(output_to_file=False)
