from modules.AstUtil import get_main_function

from typing import List, Union
from pycparser import c_ast  # type: ignore[import-untyped]
from pycparser.c_ast import FileAST  # type: ignore[import-untyped]

from helpers.HirHelper import new_temp, invert_condition, format_val, _op_eval

_else_label_counter = 0
_if_label_counter = 0

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


def _collect_inline_return_functions(ast: FileAST) -> dict[str, c_ast.Node]:
    """
    Collect very simple no-arg functions that can be inlined at compile-time.
    Supported shape:
      int foo() { return <expr>; }
    """
    inline_returns: dict[str, c_ast.Node] = {}
    for ext in ast.ext:
        if not isinstance(ext, c_ast.FuncDef):
            continue
        func_name = ext.decl.name
        if func_name == "main":
            continue

        args = getattr(ext.decl.type, "args", None)
        has_args = args is not None and getattr(args, "params", None)
        if has_args:
            continue

        body_items = getattr(ext.body, "block_items", None) or []
        if len(body_items) != 1:
            continue
        only_stmt = body_items[0]
        if not isinstance(only_stmt, c_ast.Return) or only_stmt.expr is None:
            continue
        inline_returns[func_name] = only_stmt.expr
    return inline_returns

def generate_ir_high(ast:FileAST) -> List[str]:
    lines: List[str] = []
    main_func = get_main_function(ast) 
    if main_func is None:
        raise ValueError("Main function not found in AST.")
    inline_returns = _collect_inline_return_functions(ast)

    for node in ast.ext:
        if isinstance(node, c_ast.Decl):
            if node.init is not None:
                val = gen_expr(node.init, lines, inline_returns)
                lines.append(f"{node.name} = {format_val(val)}")
            else:
                # declaration without init
                pass
        elif isinstance(node, c_ast.FuncDef):
            continue
        
        else:
            raise NotImplementedError(f"IR generation for top-level node type '{type(node).__name__}' not implemented.")

    block_items = getattr(main_func.body, 'block_items', []) or []
    lines.extend(get_ir_high(block_items, inline_returns))

    return lines
    

def get_ir_high(block_items: List[c_ast.Node], inline_returns: dict[str, c_ast.Node]) -> List[str]:
    lines : List[str] = []
    for node in block_items:
        if isinstance(node, c_ast.Decl):
            if node.init is not None:
                val = gen_expr(node.init, lines, inline_returns)
                lines.append(f"{node.name} = {format_val(val)}")
            else:
                pass
        elif isinstance(node, c_ast.Assignment):
            val = gen_expr(node.rvalue, lines, inline_returns)
            lines.append(f"{node.lvalue.name} = {format_val(val)}")
        elif isinstance(node, c_ast.If):
            cond = node.cond

            # --- Condition inside IF is always a BinaryOp ---
            if not isinstance(cond, c_ast.BinaryOp):
                raise NotImplementedError("Only BinaryOp conditions are supported in IF for now.")

            # Generate left & right operands
            left = gen_expr(cond.left, lines, inline_returns)
            right = gen_expr(cond.right, lines, inline_returns)

            # Invert operator for "jump if false" logic
            inv_op = invert_condition(cond.op)

            # Labels
            else_label = generate_else_label()
            end_label = generate_if_label()

            # Jump if condition is FALSE (inverted condition is TRUE)
            # New format: IF left inv_op right GOTO else_label
            lines.append(f"IF {format_val(left)} {inv_op} {format_val(right)} GOTO {else_label}")

            # THEN block
            then_items = getattr(node.iftrue, 'block_items', []) or [node.iftrue]
            lines.extend(get_ir_high(then_items, inline_returns))

            # After THEN, jump end (only if ELSE exists)
            if node.iffalse is not None:
                lines.append(f"GOTO {end_label}")

            # ELSE label
            lines.append(f"{else_label}:")

            # ELSE block
            if node.iffalse is not None:
                else_items = getattr(node.iffalse, 'block_items', []) or [node.iffalse]
                lines.extend(get_ir_high(else_items, inline_returns))

                # END label
                lines.append(f"{end_label}:")
        else:
            raise NotImplementedError(f"IR generation for main node type '{type(node).__name__}' not implemented.")
    return lines



def gen_expr(node: c_ast.Node, ir: List[str], inline_returns: dict[str, c_ast.Node]) -> Union[int,str]:
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
        if not node.exprs:
            raise ValueError("Empty expression list is not supported.")
        last = gen_expr(node.exprs[0], ir, inline_returns)
        for e in node.exprs[1:]:
            last = gen_expr(e, ir, inline_returns)
        return last

    # Assignment 
    if isinstance(node, c_ast.Assignment):
        rhs = gen_expr(node.rvalue, ir, inline_returns)
        lhs_name = node.lvalue.name  # assuming ID
        ir.append(f"{lhs_name} = {format_val(rhs)}")
        return lhs_name

    # UnaryOp
    if isinstance(node, c_ast.UnaryOp):
        operand = gen_expr(node.expr, ir, inline_returns)
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
        left = gen_expr(node.left, ir, inline_returns)
        right = gen_expr(node.right, ir, inline_returns)
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
        if isinstance(node.name, c_ast.ID):
            fn_name = node.name.name
            if fn_name in inline_returns:
                if node.args is not None and getattr(node.args, "exprs", None):
                    raise NotImplementedError(f"Inlined function '{fn_name}' with arguments is not supported.")
                return gen_expr(inline_returns[fn_name], ir, inline_returns)

        args = []
        if node.args:
            for a in node.args.exprs:
                args.append(gen_expr(a, ir, inline_returns))
        t = new_temp()
        args_repr = ", ".join(format_val(a) for a in args)
        ir.append(f"{t} = CALL {node.name.name}({args_repr})")
        return t

    raise NotImplementedError(f"Expression type unsupported: {type(node).__name__}")
