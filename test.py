from __future__ import annotations
import pycparser as pcp
from pycparser.c_ast import FileAST

from helpers.FileHelper import read_file
from modules.SymbolTableGen import generate_symbol_table, SymbolTable
from modules.MemoryManager import VariableManager
from modules.HIRGen import generate_ir_high
from modules.LIRGen import generate_ir_low
from modules.AssemblyGen import AssemblyGenerator

from modules.HIROptimizer import optimize_hir
from modules.LIROptimizer import optimize_lir
from entities.HirLine import HirLine
FILE_NAME = 'tests/first.c'
PARSER_DEBUG = False

def create_symbol_table():
    pass

def main():
    parser = pcp.CParser(lex_optimize=True, yacc_optimize=True)
    code = read_file(FILE_NAME)
    print(code)
    ast:FileAST = parser.parse(code, debug=PARSER_DEBUG)

    symbol_table = generate_symbol_table(ast)

    print(symbol_table.as_dict())
    hir_lines =  generate_ir_high(ast)
    print("---- HIR Lines ----")
    for line in hir_lines:
        print(line)

    optimized_hir_lines = optimize_hir(hir_lines, symbol_table)
    print("---- Optimized HIR Lines With Removed Temporaries ----")
    for line in optimized_hir_lines:
        print(line,'|', str(line.type))
    
    lir_lines = generate_ir_low(optimized_hir_lines)
    
    print("---- LIR Lines ----")
    for line in lir_lines:
        print(line)

    optimized_lir_lines = optimize_lir(lir_lines)  # You can add LIR optimizations here if needed
    
    print("---- Optimized LIR Lines ----")
    for line in optimized_lir_lines:
        print(line)
    
    assembly_generator = AssemblyGenerator(symbol_table)
    assembly_lines = assembly_generator.generate_assembly_code(optimized_lir_lines)

    print("---- Assembly Lines ----")
    for line in assembly_lines:
        print(line)
    

def lir_test():
    test_hir_lines = [
        "b = 50"
    ]

    hir_lines = HirLine.parse_hir_lines(test_hir_lines)
    lir_lines = generate_ir_low(hir_lines)
    for lir in lir_lines:
        print(lir)

if __name__ == '__main__':
    main()