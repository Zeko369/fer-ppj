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

    def instructions(self) -> list[Instruction]:
        if self.block is None:
            return [self.instruction]

        return [self.instruction] + self.block.instructions()


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
        elif self.value.startswith('KR_'):
            return 'for'
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
    prefix: str | None = field(default=None)

    def to_asm(self) -> list[str]:
        if self.type == "idn":
            return [f"LOAD R0, (var_{self.value})"]

        return [f"MOVE %D {self.value}, R0"]

    @staticmethod
    def parse(lines: list[Line]) -> "Primary":
        if len(lines) != 1:
            tmp = Primary.parse(lines[2:])
            tmp.prefix = lines[0].get_part(2)
            return tmp

        p_type = lines[0].type()
        if p_type not in ["idn", "num"]:
            raise IllegalStateError(f"Invalid primary type: {p_type}")

        return Primary(lines[0].get_part(2), p_type)  # type: ignore


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
            Primary.parse(term),
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
                inside = Line.get_subtree(lines)

                from_i = -1
                to_i = -1
                for i, l in enumerate(inside):
                    if l.get_part(0) == 'KR_DO':
                        from_i = i
                    elif l.get_part(0) == '<lista_naredbi>':
                        to_i = i
                        break

                range_from = Expression.parse(inside[3:from_i])
                range_to = Expression.parse(inside[from_i+1:to_i])
                block = InstructionBlock.parse(lines[to_i+1:-1])

                return ForLoopOperation(lines[2].get_part(2), range_from, range_to, block)
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
            f"STORE R0, ({self.get_symbol()})"
        ]

    def get_symbol(self) -> str:
        return f"var_{self.idn}"


@ dataclass
class ForLoopOperation(Operation):
    range_from: Expression
    range_to: Expression
    block: InstructionBlock | None

    def __init__(self, idn: str, range_from: Expression, range_to: Expression, block: InstructionBlock | None, *args, **kwargs):
        self.idn = idn
        self.range_from = range_from
        self.range_to = range_to
        self.block = block

        self.identifier = f"FOR_{self.idn}_{id(self)}"
        self.iterator = AssignOperation(self.identifier, self.range_from)

    def get_init(self) -> list[str]:
        return [
            *self.iterator.to_asm(),
            f"{self.identifier} ; FOR LOOP ;--"
        ]

    def get_condition(self) -> list[str]:
        return [
            f'LOAD R0, ({self.iterator.get_symbol()})',
            'ADD R0, 1, R0',
            f'STORE R0, ({self.iterator.get_symbol()})',

            *self.range_to.to_asm(),

            f'LOAD R0, ({self.iterator.get_symbol()})',
            'POP R1',
            'CMP R0, R1',
            f'JP_SLE {self.identifier}',
        ]


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
        self.parser = AST_parser(self.raw_lines)
        self.root = self.parser.run()

        self.code = [
            '; Generated by FRISC generator',
            'MOVE 40000, R7 ; stack pointer',
            '',
        ]

        self.variables: list[str] = ['var_rez']

    def handle_instructions(self, instructions: list[Instruction], s=0):
        for instruction in instructions:
            if isinstance(instruction, ForLoopOperation) and instruction.block is not None:
                self.code.append(f"; FOR_START")
                self.code.extend(instruction.get_init())

                self.code.append('; block')
                self.handle_instructions(instruction.block.instructions(), s+1)

                self.code.append(f"; condition")
                self.code.extend(instruction.get_condition())

                self.code.append(f"; FOR_END")
                self.code.append('')

                self.variables.append(instruction.iterator.get_symbol())
                continue

            if isinstance(instruction, AssignOperation) and instruction.get_symbol() not in self.variables:
                self.variables.append(instruction.get_symbol())

            self.code.append(f"; {instruction.__class__.__name__}")
            self.code.extend(instruction.to_asm())
            self.code.append('')

    def run(self, print_to_stdout=False):
        self.handle_instructions(self.root.instructions())
        self.code.append('')

        self.code.append('LOAD R6, (var_rez)')
        self.code.append('HALT')
        self.code.append('')

        self.code.append('; Global variables')
        for var in self.variables:
            self.code.append(f"{var} DW 0 ;--")

        # self.code.append('var_rez DW 0 ;--')
        # self.code.append('var_x DW 0 ;--')
        # self.code.append('var_z DW 0 ;--')
        # self.code.append('var_y DW 0 ;--')
        # self.code.append('var_i DW 0 ;--')

        with open('program.frisc', 'w') as f:
            for raw_line in self.code:
                indent = '' if raw_line.endswith('--') else '\t'
                line = f"{indent}{raw_line.split(';--')[0].strip()}"

                print(line, file=f)
                if print_to_stdout:
                    print(line)


if __name__ == '__main__':
    FRISC_generator(sys.stdin.read()).run(print_to_stdout=True)
