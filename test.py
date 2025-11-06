import pycparser as pcp
from pycparser.c_ast import FileAST,FuncDef

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

def main():
    parser = pcp.CParser(lex_optimize=True, yacc_optimize=True)
    code = read_file(FILE_NAME)
    print(code)
    ast:FileAST = parser.parse(code, debug=PARSER_DEBUG)

    main_func = get_main_function(ast)
    
    if main_func:
        print(f"Found main function: {main_func.decl.name}")
    else:
        print("Main function not found.")

    body = main_func.body
    for node in body:
        print(type(node))   

if __name__ == '__main__':
    main()