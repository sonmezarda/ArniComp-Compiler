from typing import Union

_temp_counter = 0

def new_temp() -> str:
    global _temp_counter
    name = f".t{_temp_counter}"
    _temp_counter += 1
    return name

_op_eval = {
    '+': lambda a,b: a + b,
    '-': lambda a,b: a - b,
    '*': lambda a,b: a * b,
    '/': lambda a,b: a // b if b != 0 else 0,
    '%': lambda a,b: a % b if b != 0 else 0,
    '<<': lambda a,b: a << b,
    '>>': lambda a,b: a >> b,
    '&': lambda a,b: a & b,
    '|': lambda a,b: a | b,
    '^': lambda a,b: a ^ b,
    '&&': lambda a,b: 1 if (a and b) else 0,
    '||': lambda a,b: 1 if (a or b) else 0,
    '==': lambda a,b: 1 if a == b else 0,
    '!=': lambda a,b: 1 if a != b else 0,
    '<': lambda a,b: 1 if a < b else 0,
    '<=': lambda a,b: 1 if a <= b else 0,
    '>': lambda a,b: 1 if a > b else 0,
    '>=': lambda a,b: 1 if a >= b else 0,
}

def invert_condition(op: str) -> str:
    mapping = {
        '>': '<=',
        '<': '>=',
        '>=': '<',
        '<=': '>',
        '==': '!=',
        '!=': '==',
    }
    return mapping[op]

def format_val(v: Union[int,str]) -> str:
    return str(v) if isinstance(v, int) else v