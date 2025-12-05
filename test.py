from __future__ import annotations
import pycparser as pcp
from pycparser.c_ast import FileAST

from helpers.FileHelper import read_file
from modules.SymbolTableGen import generate_symbol_table, SymbolTable
from modules.MemoryManager import VariableManager
from modules.IRGen import generate_ir_high, _op_eval

from modules.HIROptimizer import optimize_hir
from entities.HirLine import HirLine
FILE_NAME = 'tests/define.c'
PARSER_DEBUG = False

def create_symbol_table():
    pass

def generate_ir_low(hir_lines:list[HirLine]) -> list[str]:
    low_ir_lines = []
    for hir in hir_lines:
        print(hir.type)
    return low_ir_lines

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
    hir_lines =  generate_ir_high(ast)
    print("---- HIR Lines ----")
    for line in hir_lines:
        print(line)


    optimized_hir_lines = optimize_hir(hir_lines, symbol_table)
    
    print("---- Optimized HIR Lines With Removed Temporaries ----")
    for line in optimized_hir_lines:
        print(line, str(line.type))
    
    
    #lir_lines = generate_ir_low(optimized_hir_lines)


if __name__ == '__main__':
    main()