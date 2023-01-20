import re
import sys
from typing import Literal, Optional
from dataclasses import dataclass, field


class IllegalStateError(Exception):
    pass


class Instruction:
    def __init__(self):
        raise NotImplementedError

    def to_asm(self) -> str:
        raise NotImplementedError


@dataclass
class InstructionBlock:
    instruction: Instruction  # todo make this flatter
    block: Optional["InstructionBlock"]
    type: Literal["raw", "flattened"] = field(default="raw")

    _instructions: list[Instruction] = field(init=False)

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
            InstructionBlock.parse(raw_instruction_block),
            type="raw"
        )

    def flatten(self) -> list[Instruction]:
        if self.block is None:
            return [self.instruction]

        return [self.instruction] + self.block.flatten()

    @property
    def instructions(self) -> list[Instruction]:
        if self.type == "raw":
            self._instructions = self.flatten()

        return self._instructions


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

    def to_asm(self) -> list[str]:
        if self.type == "idn":
            return [f"LOAD R0, (var_{self.value})"]

        return [f"MOVE %D {self.value}, R0"]

    @staticmethod
    def parse(line: Line) -> "Primary":
        p_type = line.type()
        if p_type not in ["idn", "num"]:
            raise IllegalStateError(f"Invalid primary type: {p_type}")

        return Primary(line.get_part(2), p_type)  # type: ignore


@ dataclass
class TermList:
    op: str
    term: "Term"

    def to_asm(self) -> str:
        return f"""
        PUSH R0
        PERO
        {self.term.to_asm()}
        POP R1
        {self.op} R0, R1, R0
        """

    @staticmethod
    def parse(lines: list[Line]) -> Optional["TermList"]:
        if len(lines) <= 2:
            return None

        raise NotImplementedError


@ dataclass
class Term:
    primary: "Primary"
    t_list: TermList | None

    def to_asm(self) -> list[str]:
        if self.t_list is None:
            return [
                *self.primary.to_asm(),
                f"PUSH R0"
            ]

        return [
            f"LOAD R0, {self.primary.value}",
            self.t_list.to_asm()
        ]

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

    def to_asm(self) -> list[str]:
        return [
            *self.expression.to_asm(),
            *self.get_op(),
            "PUSH R2",
        ]

    def get_op(self) -> list[str]:
        match self.op:
            case "OP_PLUS":
                return ["POP R1", "POP R0", "ADD R0, R1, R2"]
            case "OP_MINUS":
                return ["POP R1", "POP R0", "SUB R0, R1, R2"]
            case _:
                raise NotImplementedError

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

    def to_asm(self) -> list[str]:
        if self.e_list is None:
            return self.term.to_asm()

        return [
            *self.term.to_asm(),
            *self.e_list.to_asm(),
        ]

        # return f"""
        # {self.term.to_asm()}
        # PUSH R0
        # {self.e_list.to_asm()}
        # POP R1
        # {self.e_list.op} R0, R1, R0
        # """

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

    def to_asm(self) -> list[str]:
        calc_expression = self.expression.to_asm()

        return [
            *calc_expression,
            f"POP R0",
            f"STORE R0, (var_{self.idn})"
        ]


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

    def run(self):
        parser = AST_parser(self.raw_lines)
        root = parser.run()

        code = []
        code.append('; Generated by FRISC generator')
        code.append('MOVE 40000, R7 ; stack pointer')
        code.append('')

        for instruction in root.instructions:
            asm = instruction.to_asm()
            code.append(f"; {instruction.__class__.__name__}")
            code.extend(asm)
            code.append("")

        code.append('LOAD R6, (var_rez)')
        code.append('HALT')
        code.append('')

        code.append('; Global variables')
        code.append('var_rez DW 0')
        code.append('var_x DW 0')

        for line in code:
            print(line)

        with open('program.frisc', 'w') as f:
            mode = 'tabbed'
            for line in code:
                if mode == 'tabbed':
                    print(f"\t{line}", file=f)
                else:
                    print(line, file=f)

                if line == '; Global variables':
                    mode = 'normal'


if __name__ == '__main__':
    FRISC_generator(sys.stdin.read()).run()
