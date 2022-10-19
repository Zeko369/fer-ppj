import sys

KNOWN = {'=': 'OP_PRIDRUZI', '+': 'OP_PLUS', '-': 'OP_MINUS', '*': 'OP_PUTA', '/': 'OP_DIJELI', '(': 'L_ZAGRADA', ')': 'D_ZAGRADA',
         'az': 'KR_AZ', 'za': 'KR_ZA', 'od': 'KR_OD', 'do': 'KR_DO'}


def process_line(token, i):
    if token in KNOWN:
        print(f"{KNOWN[token]} {i+1} {token}")
    elif token.isnumeric():
        print(f"BROJ {i+1} {token}")
    elif token.isidentifier():
        print(f"IDN {i+1} {token}")
    elif len(token) > 1:
        tmp = ''
        for j in token:
            tmp += j
            if j in KNOWN:
                if tmp[:-1]:
                    process_line(tmp[:-1], i)
                process_line(j, i)
                tmp = ''
        process_line(tmp, i)


def process(lines: list[str]):
    for i, line in enumerate([rl.split('//')[0].strip() for rl in lines]):
        for token in line.split():
            process_line(token, i)


if __name__ == '__main__':
    process(sys.stdin.readlines())
