import sys


class SemanticAnalyzer:
    def __init__(self, input):
        self.input = input
        self.lines = input.splitlines()

        self.global_vars: dict[str, int] = {}
        self.scope_vars: list[dict[str, int]] = []

    def run(self):
        loop = 0

        i = 1
        while i < len(self.lines):
            line = self.lines[i]
            line_type = self.get_type(line)

            if line_type == 'KR_ZA':
                loop += 1
                self.scope_vars.append({})
            elif line_type == 'KR_AZ':
                loop -= 1
                self.scope_vars.pop()
            elif line_type == 'IDN':
                idn = self.get_identifier(line)
                line_number = self.get_line(line)
                next_line_type = self.get_type(self.lines[i + 1])

                if next_line_type == 'OP_PRIDRUZI':
                    if loop == 0 and idn not in self.global_vars:
                        self.global_vars[idn] = line_number
                    if loop > 0 and idn not in self.global_vars and idn not in self.scope_vars[-1]:
                        self.scope_vars[-1][idn] = line_number

                    i += 1
                    continue

                if next_line_type == 'KR_OD':
                    self.scope_vars[-1][idn] = line_number
                    i += 1
                    continue

                def_line_number = self.is_local(idn)
                if def_line_number is None:
                    def_line_number = self.global_vars.get(idn)

                if def_line_number == line_number:
                    def_line_number = None

                if def_line_number is None:
                    print('err', line_number, idn)
                    break

                print(line_number, def_line_number, idn)

            i += 1

    def is_local(self, idn: str):
        for scope in self.scope_vars:
            if idn in scope:
                return scope[idn]

    def get_line(self, line: str):
        return int(line.strip().split(' ')[1])

    def get_type(self, line: str):
        return line.strip().split(' ')[0]

    def get_identifier(self, line: str):
        if self.get_type(line) != 'IDN':
            raise Exception('Not an identifier')

        return line.strip().split(' ')[2]


if __name__ == '__main__':
    SemanticAnalyzer(sys.stdin.read()).run()
