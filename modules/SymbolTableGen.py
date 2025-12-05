from enum import StrEnum
from pycparser.c_ast import FileAST,FuncDef, Decl, Constant

from entities.SymbolTable import *

def get_function_return_type(func_def:FuncDef) -> SymbolType:
    type_str = func_def.decl.type.type.type.names[0]
    return SymbolType(type_str)

def get_variable_type(decl:Decl) -> SymbolType:
    type_str = decl.type.type.names[0]
    return SymbolType(type_str)

def get_qualifier(decl:Decl) -> SymbolQualifier | None:
    if 'const' in decl.quals:
        return SymbolQualifier.CONST
    if 'volatile' in decl.quals:
        return SymbolQualifier.VOLATILE
    return None

def create_variable_symbol(decl:Decl, scope:SymbolScope) -> Symbol:
    var_name = decl.name
    var_type = get_variable_type(decl)
    var_qualifier = get_qualifier(decl)
    var_symbol = Symbol(
        name=var_name,
        kind=SymbolKind.VARIABLE,
        type=var_type,
        scope=scope,
        qualifier=var_qualifier
    )
    return var_symbol

def generate_symbol_table(ast:FileAST)  -> SymbolTable:
    symbol_table = SymbolTable()
    for ext in ast.ext:
        if isinstance(ext, FuncDef):
            func_name = ext.decl.name

            body = ext.body
            for stmt in body.block_items:
                if isinstance(stmt, Decl):
                    var_symbol = create_variable_symbol(stmt, SymbolScope.GLOBAL if func_name == 'main' else SymbolScope.LOCAL)
                    symbol_table.add_symbol(var_symbol)

            if func_name == 'main':
                continue
            func_return_type =  get_function_return_type(ext)
            print("return type", func_return_type)
            func_symbol = Symbol(
                name=func_name,
                kind=SymbolKind.FUNCTION,
                type=func_return_type,
                scope=SymbolScope.GLOBAL,
                qualifier=None
            )
            symbol_table.add_symbol(func_symbol)
        elif isinstance(ext, Decl):
            var_symbol = create_variable_symbol(ext, SymbolScope.GLOBAL)
            symbol_table.add_symbol(var_symbol)
            print(f"Variable: {var_symbol.name}")
        else:
            print("Unknown external declaration")
            print(type(ext))
        
    return symbol_table
