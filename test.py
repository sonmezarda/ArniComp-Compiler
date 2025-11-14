import pycparser as pcp
from pycparser.c_ast import FileAST,FuncDef, Decl, Constant

from modules.FileHelper import read_file
from modules.SymbolTableGen import generate_symbol_table
from modules.MemoryManager import VariableManager
FILE_NAME = 'tests/define.c'
PARSER_DEBUG = False

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
    for ext in ast.ext:
        if isinstance(ext, Decl):
            if ext.init:
                if isinstance(ext.init, Constant):
                    lines.append(__IR_store(ext, ext.init.value))
            else:
                lines.append(__IR_declare(ext))
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



def generate_assembly(ir_lines:list[str]) -> list[str]:
    asm_lines = []
    for ir in ir_lines:
        parts = ir.split()
        if parts[0] == "DECLARE":
            asm_lines.append(f"ALLOCATE {parts[1]}")
        elif parts[0] == "STORE":
            asm_lines.append(f"MOV {parts[2]} -> {parts[1]}")
    return asm_lines


def main():
    parser = pcp.CParser(lex_optimize=True, yacc_optimize=True)
    vm = VariableManager()
    code = read_file(FILE_NAME)
    print(code)
    ast:FileAST = parser.parse(code, debug=PARSER_DEBUG)

    symbol_table = generate_symbol_table(ast)
    vm.load_symbol_table(symbol_table)
    vm.print_variables()
    print(symbol_table.as_dict())
    ir_lines =  generete_ir(ast)
    for line in ir_lines:
        print(line)

if __name__ == '__main__':
    main()