import pycparser as pcp
from pycparser.c_ast import FileAST
from modules.FileHelper import read_file
from modules.SymbolTableGen import generate_symbol_table
from modules.MemoryManager import VariableManager
from modules.IRGen import generate_ir_high

FILE_NAME = 'tests/define.c'
PARSER_DEBUG = False



def create_symbol_table():
    pass



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
    ir_lines =  generate_ir_high(ast)
    for line in ir_lines:
        print(line)

if __name__ == '__main__':
    main()