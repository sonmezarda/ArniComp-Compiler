from pycparser.c_ast import FileAST, Decl, Constant
import pycparser.c_ast as c_ast

from modules.AstUtil import get_main_function

temp_counter = 0
def new_temp() -> str:
    global temp_counter
    t = f".t{temp_counter}"
    temp_counter += 1
    return t


def gen_expr(node, ir) -> str|None:
    if isinstance(node, c_ast.Constant):
        t = new_temp()
        ir.append(f"{t} = {node.value}")
        return t

    if isinstance(node, c_ast.ID):
        return node.name

    if isinstance(node, c_ast.UnaryOp):
        operand = gen_expr(node.expr, ir)

        op = node.op

        t = new_temp()
        if op == '-':
            ir.append(f"{t} = neg {operand}")
        elif op == '!':
            ir.append(f"{t} = not {operand}")
        elif op == '~':
            ir.append(f"{t} = bitnot {operand}")
        else:
            raise NotImplementedError(f"Unary operator '{op}' IR yok")

        return t
    
    if isinstance(node, c_ast.BinaryOp):
        left = gen_expr(node.left, ir)
        right = gen_expr(node.right, ir)

        t = new_temp()
        op = node.op
        ir.append(f"{t} = {left} {op} {right}")
        return t

    if isinstance(node, c_ast.Assignment):
        rhs = gen_expr(node.rvalue, ir)
        lhs = node.lvalue.name  

        ir.append(f"{lhs} = {rhs}")
        return lhs

    if isinstance(node, c_ast.ExprList):
        last_temp = None
        for e in node.exprs:
            last_temp = gen_expr(e, ir)
        return last_temp

    raise NotImplementedError(f"Expression type unsupported: {type(node).__name__}")



def generete_ir(ast:FileAST) -> list[str]:
    lines = []
    main_func = get_main_function(ast)
    for node in ast.ext:
        if isinstance(node, Decl):
            if node.init:
                temp = gen_expr(node.init, lines)
                lines.append(f"{node.name} = {temp}")
                lines.append(__IR_store(node, temp))
            else:
                pass

        elif isinstance(node, c_ast.FuncDef):
            continue
        else:
            raise NotImplementedError(f"IR generation for node type '{type(node).__name__}' is not implemented.")

    for node in main_func.body:
        if isinstance(node, Decl):
            if node.init:
                temp = gen_expr(node.init, lines)
                lines.append(f"{node.name} = {temp}")
                lines.append(__IR_store(node, temp))
            else:
                pass
        else:
            raise NotImplementedError(f"IR generation for node type '{type(node).__name__}' is not implemented.")
    return lines

def __IR_store(node:Decl, value:str) -> str:
    return f"STORE {node.name} {value}"

def __IR_declare(node:Decl) -> str:
    return f"DECLARE {node.name}"


if __name__ == '__main__':
    pass
