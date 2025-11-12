import pycparser as pcp
from pycparser.c_ast import FileAST,FuncDef, Decl, Constant

FILE_NAME = 'tests/define.c'
PARSER_DEBUG = False
def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()

def get_main_function(ast:FileAST) -> FuncDef | None:
    for ext in ast.ext:
        if isinstance(ext, FuncDef):
            if ext.decl.name == 'main':
                return ext
    return None

def create_symbol_table():
    pass

def generete_ir(ast:FileAST):
    lines = []
    main_func = get_main_function(ast)
    for node in main_func.body:
        if isinstance(node, Decl):
            if node.init:
                if isinstance(node.init, Constant):
                    lines.append(__IR_store(node, node.init.value))
            else:
                lines.append(__IR_declare(node))
    return lines

def __IR_store(node:Decl, value:str) -> str:
    return f"STORE {node.name} {value}"

def __IR_declare(node:Decl) -> str:
    return f"DECLARE {node.name}"

def main():
    parser = pcp.CParser(lex_optimize=True, yacc_optimize=True)
    code = read_file(FILE_NAME)
    print(code)
    ast:FileAST = parser.parse(code, debug=PARSER_DEBUG)

    ir_lines =  generete_ir(ast)
    for line in ir_lines:
        print(line)

if __name__ == '__main__':
    main()