import re
import sys
import pprint
from typing import Literal, Optional, List
from dataclasses import dataclass, field


MULTIPLY_AND_DIVIDE_OPERATIONS = """
MD_SGN MOVE 0, R6 ;--
    XOR R0, 0, R0
    JP_P MD_TST1
    XOR R0, -1, R0
    ADD R0, 1, R0
    MOVE 1, R6
MD_TST1 XOR R1, 0, R1 ;--
    JP_P MD_SGNR
    XOR R1, -1, R1
    ADD R1, 1, R1
    XOR R6, 1, R6
MD_SGNR RET ;--
MD_INIT POP R4 ; MD_INIT ret addr ;--
    POP R3 ; M/D ret addr
    POP R1 ; op2
    POP R0 ; op1
    CALL MD_SGN
    MOVE 0, R2 ; init rezultata
    PUSH R4 ; MD_INIT ret addr
    RET
MD_RET XOR R6, 0, R6 ; predznak? ;--
    JP_Z MD_RET1
    XOR R2, -1, R2 ; promijeni predznak
    ADD R2, 1, R2
MD_RET1 POP R4 ; MD_RET ret addr ;--
    PUSH R2 ; rezultat
    PUSH R3 ; M/D ret addr
    PUSH R4 ; MD_RET ret addr
    RET
MUL CALL MD_INIT ;--
    XOR R1, 0, R1
    JP_Z MUL_RET ; op2 == 0
    SUB R1, 1, R1
MUL_1 ADD R2, R0, R2 ;--
    SUB R1, 1, R1
    JP_NN MUL_1 ; >= 0?
MUL_RET CALL MD_RET ;--
    RET
DIV CALL MD_INIT ;--
    XOR R1, 0, R1
    JP_Z DIV_RET ; op2 == 0
DIV_1 ADD R2, 1, R2 ;--
    SUB R0, R1, R0
    JP_NN DIV_1
    SUB R2, 1, R2
DIV_RET CALL MD_RET ;--
    RET
"""


class IllegalStateError(Exception):
    pass


class ScopeStore:
    def __init__(self) -> None:
        self.variables = {}
        self.scopes: dict[str, ScopeStore] = {}

    def list(self) -> List[str]:
        return [
            *self.variables.values(),
            *[v for s in self.scopes.values() for v in s.list()]
        ]


class VariableStore:
    def __init__(self):
        self.reset()

    def reset(self):
        self.store = ScopeStore()
        self.store.variables = {'rez': 'GLOBAL_RESULT'}

    def add(self, name: str, path: List[str], idn: str):
        if len(path) == 0:
            self.store.variables[name] = idn
            return
        pointer = self.store
        for scope in path:
            if scope not in pointer.scopes:
                pointer.scopes[scope] = ScopeStore()
            pointer = pointer.scopes[scope]

        pointer.variables[name] = idn

    def exists(self, name: str, path: List[str] = []):
        try:
            self.get(name, path)
            return True
        except KeyError:
            return False

    def get(self, name: str, path: List[str] = []):
        if len(path) == 0:
            return self.store.variables[name]

        for s in range(len(path), -1, -1):
            pointer = self.store
            for scope in path[:s]:
                if scope not in pointer.scopes:
                    break

                pointer = pointer.scopes[scope]

            if name in pointer.variables:
                return pointer.variables[name]

        raise KeyError(f"Variable {name} not found in scope {path}")

    def list(self):
        return self.store.list()


store = VariableStore()


class Instruction:
    def __init__(self):
        raise NotImplementedError

    def to_asm(self, scope: List[str]) -> str:
        raise NotImplementedError


@dataclass
class InstructionBlock:
    instruction: Instruction  # todo make this flatter
    block: Optional["InstructionBlock"]
    type: Literal["raw", "flattened"] = field(default="raw")

    @staticmethod
    def parse(lines: List["Line"]) -> "InstructionBlock | None":
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

    def instructions(self) -> List[Instruction]:
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
    def get_subtree(lines: List["Line"]) -> List["Line"]:
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
    prefix: str = field(default="")

    def to_asm(self, scope: List[str]) -> List[str]:
        if self.type == "idn":
            return [f"LOAD R0, ({store.get(self.value, scope)})"]

        return [f"MOVE %D {self.prefix}{self.value}, R0"]

    @staticmethod
    def parse(lines: List[Line]) -> "Primary":
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

    def to_asm(self, scope: List[str]) -> List[str]:
        return [
            'PUSH R0',
            *self.term.to_asm(scope),
            *self.get_op(),
        ]

    def get_op(self) -> List[str]:
        pops = []

        if self.op == "OP_PUTA":
            return [*pops, "CALL MUL"]
        elif self.op == "OP_DIJELI":
            return [*pops, "CALL DIV"]
        else:
            raise NotImplementedError

    @staticmethod
    def parse(lines: List[Line]) -> Optional["TermList"]:
        items = Line.get_subtree(lines[0:])

        return TermList(
            items[0].get_part(0),
            Term.parse(items[2:])
        )


@ dataclass
class Term:
    primary: "Primary"
    t_list: TermList | None

    def to_asm(self, scope: List[str]) -> List[str]:
        if self.t_list is None:
            return [
                *self.primary.to_asm(scope),
                f"PUSH R0"
            ]

        return [
            *self.primary.to_asm(scope),
            *self.t_list.to_asm(scope)
        ]

    @staticmethod
    def parse(lines: List[Line]) -> "Term":
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

    def to_asm(self, scope: List[str]) -> List[str]:
        return [
            *self.expression.to_asm(scope),
            *self.get_op(),
            "PUSH R2",
        ]

    def get_op(self) -> List[str]:
        pops = ["POP R1", "POP R0"]
        if self.op == "OP_PLUS":
            return [*pops, "ADD R0, R1, R2"]
        elif self.op == "OP_MINUS":
            return [*pops, "SUB R0, R1, R2"]
        else:
            raise NotImplementedError

    @staticmethod
    def parse(lines: List[Line]) -> Optional["ExpressionList"]:
        items = Line.get_subtree(lines[0:])

        return ExpressionList(
            items[0].get_part(0),
            Expression.parse(items[1:])
        )


@ dataclass
class Expression:
    term: Term
    e_list: ExpressionList | None

    def to_asm(self, scope: List[str]) -> List[str]:
        if self.e_list is None:
            return self.term.to_asm(scope)

        return [
            *self.term.to_asm(scope),
            *self.e_list.to_asm(scope),
        ]

    @staticmethod
    def parse(lines: List[Line]) -> "Expression":
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
    def parse(lines: List[Line]) -> "Operation":
        if lines[0].value == '<naredba_pridruzivanja>':
            assignment = Line.get_subtree(lines)
            return AssignOperation(
                assignment[0].get_part(2),
                Expression.parse(assignment[2:])
            )
        elif lines[0].value == '<za_petlja>':
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
        else:
            raise NotImplementedError


@ dataclass
class AssignOperation(Operation):
    expression: Expression

    def to_asm(self, scope: List[str]) -> List[str]:
        if self.expression.e_list is None and self.expression.term.t_list is None:
            return [
                *self.expression.term.primary.to_asm(scope),
                f"STORE R0, ({self.get_symbol(scope)})"
            ]

        calc_expression = self.expression.to_asm(scope)

        return [
            *calc_expression,
            f"POP R0",
            f"STORE R0, ({self.get_symbol(scope)})"
        ]

    def get_symbol(self, scope: List[str]) -> str:
        return store.get(self.idn, scope)


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

        self.uuid = f"FOR_{self.idn}_{id(self)}"
        self.iterator = AssignOperation(self.idn, self.range_from)

    def get_init(self, scope: List[str]) -> List[str]:
        return [
            *self.iterator.to_asm(scope),
            f"{self.uuid} ; FOR LOOP ;--"
        ]

    def get_condition(self, scope: List[str]) -> List[str]:
        return [
            f'LOAD R0, ({self.iterator.get_symbol(scope)})',
            'ADD R0, 1, R0',
            f'STORE R0, ({self.iterator.get_symbol(scope)})',

            *self.range_to.to_asm(scope),

            f'LOAD R0, ({self.iterator.get_symbol(scope)})',
            'POP R1',
            'CMP R0, R1',
            f'JP_SLE {self.uuid}',
        ]


class AST_parser:
    def __init__(self, lines: List[str]):
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
            ''
        ]

    def handle_instructions(self, instructions: List[Instruction], scope=[]):
        for instruction in instructions:
            if isinstance(instruction, ForLoopOperation):
                if instruction.block is None:
                    continue

                inner_path = [*scope, instruction.uuid]

                store.add(instruction.idn, inner_path,
                          f"{instruction.uuid}_var")

                self.code.append(f"; FOR_START")
                self.code.extend(instruction.get_init(inner_path))

                self.code.append(f'; block')
                self.handle_instructions(
                    instruction.block.instructions(),
                    inner_path
                )

                self.code.append(f"; condition")
                self.code.extend(instruction.get_condition(inner_path))

                self.code.append(f"; FOR_END")
                self.code.append('')

                continue

            if isinstance(instruction, AssignOperation):
                if not store.exists(instruction.idn, scope):
                    unique_path = [*scope, instruction.idn]
                    store.add(instruction.idn, scope, "__".join(unique_path))

            self.code.append(f"; {instruction.__class__.__name__}")
            self.code.extend(instruction.to_asm(scope))
            self.code.append('')

    def run(self, output_file: str, print_to_stdout=False):
        self.handle_instructions(self.root.instructions())
        self.code.append('')

        self.code.append(f'LOAD R6, ({store.get("rez")})')
        self.code.append('HALT')
        self.code.append('')

        self.code.append('; Global variables')
        for var in store.list():
            self.code.append(f"{var} DW 0 ;--")

        self.code.append('')
        self.code.extend(MULTIPLY_AND_DIVIDE_OPERATIONS.splitlines())

        with open(output_file, 'w') as f:
            for raw_line in self.code:
                indent = '' if raw_line.endswith('--') else '\t'
                line = f"{indent}{raw_line.split(';--')[0].strip()}"

                print(line, file=f)
                if print_to_stdout:
                    print(line)


if __name__ == '__main__':
    name = 'a.frisc' if len(sys.argv) < 2 else sys.argv[1]
    FRISC_generator(sys.stdin.read()).run(name, print_to_stdout=False)
