from modules.AstUtil import get_main_function

from typing import List, Union
from pycparser import c_ast
from pycparser.c_ast import FileAST

_temp_counter = 0
_else_label_counter = 0
_if_label_counter = 0

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

def generate_else_label() -> str:
    global _else_label_counter
    name = f".Lelse{_else_label_counter}"
    _else_label_counter += 1
    return name

def generate_if_label() -> str:
    global _if_label_counter
    name = f".Lif{_if_label_counter}"
    _if_label_counter += 1
    return name

def generate_ir_high(ast:FileAST) -> List[str]:
    lines: List[str] = []
    main_func = get_main_function(ast) 

    for node in ast.ext:
        if isinstance(node, c_ast.Decl):
            if node.init is not None:
                val = gen_expr(node.init, lines)
                lines.append(f"{node.name} = {format_val(val)}")
            else:
                # declaration without init
                pass
        elif isinstance(node, c_ast.FuncDef):
            continue
        
        else:
            raise NotImplementedError(f"IR generation for top-level node type '{type(node).__name__}' not implemented.")

    block_items = getattr(main_func.body, 'block_items', []) or []
    lines.extend(get_ir_high(block_items))

    return lines
    

def get_ir_high(block_items: List[c_ast.Node]) -> List[str]:
    lines : List[str] = []
    for node in block_items:
        if isinstance(node, c_ast.Decl):
            if node.init is not None:
                val = gen_expr(node.init, lines)
                lines.append(f"{node.name} = {format_val(val)}")
            else:
                pass
        elif isinstance(node, c_ast.Assignment):
            val = gen_expr(node.rvalue, lines)
            lines.append(f"{node.lvalue.name} = {format_val(val)}")
        elif isinstance(node, c_ast.If):
            cond = node.cond

            # --- Condition inside IF is always a BinaryOp ---
            if not isinstance(cond, c_ast.BinaryOp):
                raise NotImplementedError("Only BinaryOp conditions are supported in IF for now.")

            # Generate left & right
            left = gen_expr(cond.left, lines)
            right = gen_expr(cond.right, lines)

            # Invert operator
            inv_op = invert_condition(cond.op)

            # Allocate temp for inverted condition
            t_cond = new_temp()
            lines.append(f"{t_cond} = {format_val(left)} {inv_op} {format_val(right)}")

            # Labels
            else_label = generate_else_label()
            end_label = generate_if_label()

            # Jump if condition is FALSE
            lines.append(f"IF {t_cond} GOTO {else_label}")

            # THEN block
            then_items = getattr(node.iftrue, 'block_items', []) or [node.iftrue]
            lines.extend(get_ir_high(then_items))

            # After THEN, jump end (only if ELSE exists)
            if node.iffalse is not None:
                lines.append(f"GOTO {end_label}")

            # ELSE label
            lines.append(f"{else_label}:")

            # ELSE block
            if node.iffalse is not None:
                else_items = getattr(node.iffalse, 'block_items', []) or [node.iffalse]
                lines.extend(get_ir_high(else_items))

                # END label
                lines.append(f"{end_label}:")
        else:
            raise NotImplementedError(f"IR generation for main node type '{type(node).__name__}' not implemented.")
    return lines

def format_val(v: Union[int,str]) -> str:
    return str(v) if isinstance(v, int) else v

def gen_expr(node: c_ast.Node, ir: List[str]) -> Union[int,str]:
    # Constant
    if isinstance(node, c_ast.Constant):
        try:
            return int(node.value, 0)
        except Exception:
            return int(node.value)

    # Identifier
    if isinstance(node, c_ast.ID):
        return node.name

    # ExprList
    if isinstance(node, c_ast.ExprList):
        last = None
        for e in node.exprs:
            last = gen_expr(e, ir)
        return last

    # Assignment 
    if isinstance(node, c_ast.Assignment):
        rhs = gen_expr(node.rvalue, ir)
        lhs_name = node.lvalue.name  # assuming ID
        ir.append(f"{lhs_name} = {format_val(rhs)}")
        return lhs_name

    # UnaryOp
    if isinstance(node, c_ast.UnaryOp):
        operand = gen_expr(node.expr, ir)
        op = node.op
        # constant fold
        if isinstance(operand, int):
            if op == '-':
                return -operand
            if op == '~':
                return ~operand
            if op == '!':
                return 0 if operand else 1
        t = new_temp()
        if op == '-':
            ir.append(f"{t} = neg {operand}")
        elif op == '~':
            ir.append(f"{t} = bitnot {operand}")
        elif op == '!':
            ir.append(f"{t} = not {operand}")
        else:
            raise NotImplementedError(f"Unary operator '{op}' not supported.")
        return t

    # BinaryOp
    if isinstance(node, c_ast.BinaryOp):
        left = gen_expr(node.left, ir)
        right = gen_expr(node.right, ir)
        op = node.op

        # constant folding
        if isinstance(left, int) and isinstance(right, int) and op in _op_eval:
            try:
                return _op_eval[op](left, right)
            except Exception:
                pass

        # Avoid creating temps for trivial cases
        t = new_temp()
        ir.append(f"{t} = {format_val(left)} {op} {format_val(right)}")
        return t

    # FuncCall 
    if isinstance(node, c_ast.FuncCall):
        args = []
        if node.args:
            for a in node.args.exprs:
                args.append(gen_expr(a, ir))
        t = new_temp()
        args_repr = ", ".join(format_val(a) for a in args)
        ir.append(f"{t} = CALL {node.name.name}({args_repr})")
        return t

    raise NotImplementedError(f"Expression type unsupported: {type(node).__name__}")
