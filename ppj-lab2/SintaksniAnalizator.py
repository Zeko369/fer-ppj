import sys
from typing import Union


class SyntaxError(Exception):
    def __init__(self, message: Union[str, list]):
        self.message = ' '.join(message) if isinstance(
            message, list) else message

    def __str__(self):
        return f"err {self.message}"


class SyntaxAnalyzer:
    def __init__(self, text: str):
        self.instructions = []
        self.raw_lines = list(map(lambda x: x.split(), text.splitlines()))

        self.iLine = 0
        self.iInst = 0

        self.indent = 0
        self.buffer = []

    def run(self):
        try:
            self._process()
            print('\n'.join(self.buffer))
        except SyntaxError as e:
            print(e)

    def _process(self):
        dict = {}
        for line in self.raw_lines:
            line_number = int(line[1])
            if line_number not in dict:
                dict[line_number] = []

            dict[line_number].append(line)

        for k in sorted(dict.keys()):
            self.instructions.append(dict[k])

        self._check_parentheses()

        self._print('<program>', 1)

        self._process_instruction_list()

        self.iLine = 0
        if len(self.instructions) > 0 and len(self.instructions[self.iLine]) == 0:
            raise SyntaxError('kraj')

    def _check_parentheses(self):
        add = False
        last = ""
        count = 0

        for line in self.instructions:
            if add and line[0][0] == 'IDN':
                add = False
                last = line[0]

            for instruction in line:
                if instruction[0] == 'L_ZAGRADA':
                    add = True
                    count += 1
                elif instruction[0] == 'D_ZAGRADA':
                    add = True
                    count -= 1

        if count != 0:
            raise SyntaxError(last)

    def _print(self, text: Union[str, tuple], indent=0):
        if isinstance(text, list):
            text = ' '.join(text)

        self.buffer.append(f"{' ' * self.indent}{text}")
        self.indent += indent

    def _process_instruction_list(self):
        self._print('<lista_naredbi>', 1)

        if self.iLine >= len(self.instructions):
            self._print('$', -1)
            return

        if self.__get_instruction() == 'IDN' or self.__get_instruction() == 'KR_ZA':
            self._process_instruction()
            self.iLine += 1
            self.iInst = 0
            self._process_instruction_list()
        elif self.__get_instruction() == 'KR_AZ':
            self._print('$')
        elif self.__get_instruction() == 'OP_PRIDRUZI':
            raise SyntaxError(self.instructions[self.iLine][self.iInst])

        self.indent -= 1

    def _process_instruction(self):
        self._print('<naredba>', 1)

        if self.__get_instruction() == 'IDN':
            self._process_assignment()
        elif self.__get_instruction() == 'KR_ZA':
            self._process_for()

        self.indent -= 1

    def _process_assignment(self):
        self._print('<naredba_pridruzivanja>', 1)
        for i in range(2):
            self._print(self.instructions[self.iLine][self.iInst])
            self.iInst += 1

        if self.iInst >= len(self.instructions[self.iLine]) and self.instructions[self.iLine][self.iInst - 1][0] == 'OP_PRIDRUZI' and self.iLine + 1 >= len(self.instructions):
            raise SyntaxError('kraj')

        if self.iInst >= len(self.instructions[self.iLine]):
            self.iLine += 1
            self.iInst = 0

            if self.instructions[self.iLine][self.iInst + 1][0] == 'OP_PRIDRUZI':
                raise SyntaxError(
                    self.instructions[self.iLine][self.iInst + 1])

        self.__e()

        if self.__get_instruction() == 'OP_PRIDRUZI':
            self._print('$')
            self.iInst += 1

        self.indent -= 1

    def _process_for(self):
        self._print('<za_petlja>', 1)
        for i in range(3):
            self._print(self.instructions[self.iLine][self.iInst])
            self.iInst += 1

        if self.__get_instruction() in ["OP_MINUS", "OP_PLUS", "BROJ", "IDN", "L_ZAGRADA"]:
            self.__e()
        else:
            raise SyntaxError(self.instructions[self.iLine][self.iInst])

        self._print(self.instructions[self.iLine][self.iInst])
        self.iInst += 1

        if self.__get_instruction() in ["OP_MINUS", "OP_PLUS", "BROJ", "IDN", "L_ZAGRADA"]:
            self.__e()
        else:
            raise SyntaxError(self.instructions[self.iLine][self.iInst - 1])

        self.iLine += 1
        self.iInst = 0

        self._process_instruction_list()

        self._print(self.instructions[self.iLine][0])
        self.indent -= 1

    def __get_instruction(self):
        return self.instructions[self.iLine][self.iInst][0]

    def __te_builder(self, label, run_fn, list_fn):
        self._print(f'<{label}>', 1)
        if self.__get_instruction() in ['IDN', 'BROJ', 'OP_PLUS', 'OP_MINUS', 'L_ZAGRADA']:
            run_fn()
            list_fn()

        self.indent -= 1

    def __e(self): self.__te_builder('E', self.__t, self.__e_list)
    def __t(self): self.__te_builder('T', self.__p, self.__t_list)

    def __e_list(self):
        self._print('<E_lista>', 1)

        if self.iInst >= len(self.instructions[self.iLine]):
            self._print('$', -1)
            self.iInst -= 1
            return

        if self.__get_instruction() in ["IDN", "D_ZAGRADA", "KR_ZA", "KR_DO", "KR_AZ"]:
            self._print('$')
        elif self.__get_instruction() in ["OP_PLUS", "OP_MINUS"]:
            self._print(self.instructions[self.iLine][self.iInst])
            self.iInst += 1

            self.__e()

        self.indent -= 1

    def __t_list(self):
        self._print('<T_lista>', 1)

        if self.iInst >= len(self.instructions[self.iLine]):
            self._print('$', -1)
            return

        if self.__get_instruction() in ["IDN", "D_ZAGRADA", "OP_PLUS", "OP_MINUS", "KR_ZA", "KR_DO", "KR_AZ"]:
            self._print('$')
        elif self.__get_instruction() in ["OP_PUTA", "OP_DIJELI"]:
            self._print(self.instructions[self.iLine][self.iInst])
            self.iInst += 1

            self.__t()

        self.indent -= 1

    def __p(self):
        self._print('<P>', 1)

        if self.__get_instruction() in ['IDN', 'BROJ']:
            self._print(self.instructions[self.iLine][self.iInst])
            self.iInst += 1
        elif self.__get_instruction() in ['OP_PLUS', 'OP_MINUS']:
            self._print(self.instructions[self.iLine][self.iInst])

            self.iInst += 1
            if self.__get_instruction() in ['IDN', 'BROJ', 'OP_PLUS', 'OP_MINUS', 'L_ZAGRADA']:
                self.__p()
                self.indent -= 1
                return

            self.__e_list()
        elif self.__get_instruction() == 'L_ZAGRADA':
            self._print(self.instructions[self.iLine][self.iInst])
            self.iInst += 1

            self.__e()
            self.__right_parentheses()

        self.indent -= 1

    def __right_parentheses(self):
        if self.__get_instruction() == 'D_ZAGRADA':
            self._print(self.instructions[self.iLine][self.iInst])
        self.iInst += 1


if __name__ == '__main__':
    SyntaxAnalyzer(sys.stdin.read()).run()
