from __future__ import annotations

from entities.HirLine import *
from entities.SymbolTable import SymbolTable

def remove_unused_temporaries(hir_lines:list[HirLine]) -> list[HirLine]:
    optimized_hir_lines = []
    used_temps_count : dict[str, int] = get_temp_vars_used_count(hir_lines)
    is_next_to_remove = False
    for (i, hir) in enumerate(hir_lines):
        if is_next_to_remove:
            is_next_to_remove = False
            continue
        if isinstance(hir, ArithmeticOpHirLine):
            if hir.result_var.startswith('.t'):
                if used_temps_count.get(hir.result_var, 0) == 2:
                    if hir_lines[i+1].type in [HirLineType.ASSIGNMENT]:
                        next_hir : AssignmentHirLine = hir_lines[i+1]
                        hir : ArithmeticOpHirLine = hir
                        optimized_hir_lines.append(ArithmeticOpHirLine(f"{next_hir.var_name} = {hir.left_operand} {hir.operator} {hir.right_operand}"))
                        is_next_to_remove = True
                        continue
        
        optimized_hir_lines.append(hir)
    return  optimized_hir_lines

def find_static_vars(hir_lines:list[HirLine], symbol_table: SymbolTable) -> dict[str,int]:
    static_vars = {}
    for i, hir in enumerate(hir_lines):
        if isinstance(hir, AssignmentHirLine):
            var_symbol =  symbol_table.get(hir.var_name)
            if var_symbol.qualifier == 'volatile':
                continue
            if is_variable_assigned(hir_lines[i+1:], hir.var_name):
                continue
            static_vars[hir.var_name] = hir.value
    return static_vars

def paste_static_vars(hir_lines:list[HirLine], static_vars:dict[str,int]) -> list[HirLine]:
    pasted_hir_lines = []
    for hir in hir_lines:
        if isinstance(hir, AssignmentHirLine):
            if hir.var_name in static_vars:
                continue
        elif isinstance(hir, ArithmeticOpHirLine):
            if hir.left_operand in static_vars:
                hir.set_left_operand(static_vars[hir.left_operand])
            if hir.right_operand in static_vars:
                hir.set_right_operand(static_vars[hir.right_operand])

        elif isinstance(hir, ConditionalOpHirLine):
            if hir.left_operand in static_vars:
                hir.set_left_operand(static_vars[hir.left_operand])
            if hir.right_operand in static_vars:
                hir.set_right_operand(static_vars[hir.right_operand])
        pasted_hir_lines.append(hir)
    return pasted_hir_lines

def is_variable_assigned(hir_lines:list[HirLine], var_name:str) -> bool:
    for hir in hir_lines:
        if isinstance(hir, AssignmentHirLine):
            if hir.var_name == var_name:
                return True
        if isinstance(hir, ArithmeticOpHirLine) or isinstance(hir, ConditionalOpHirLine):
            if hir.result_var == var_name:
                return True
    return False

def check_var_used(hir_lines:list[str]):
    used_vars = set()
    for hir in hir_lines:
        tokens = hir.split()
        for token in tokens:
            if token.startswith('.t'):
                used_vars.add(token)
    return used_vars

def get_var_used_count(hir_lines:list[HirLine], symbol_table:SymbolTable) -> dict[str,int]:
    used_vars_count = {}
    for hir in hir_lines:
        splitted = hir.splitted
        for token in splitted:
            if token.startswith('.t') or symbol_table.is_exists(token):
                if token in used_vars_count:
                    used_vars_count[token] += 1
                else:
                    used_vars_count[token] = 1
    return used_vars_count


def is_line_exists(hir_lines:list[HirLine], target_line:str) -> bool:
    for hir in hir_lines:
        if hir.line == target_line:
            return True
    return False

def get_temp_vars_used_count(hir_lines:list[HirLine]) -> dict[str,int]:
    used_temps_count = {}
    for hir in hir_lines:
        splitted = hir.splitted
        for token in splitted:
            if token.startswith('.t'):
                if token in used_temps_count:
                    used_temps_count[token] += 1
                else:
                    used_temps_count[token] = 1
    return used_temps_count

def _extract_value_from_line(hir: HirLine):
    """producer satırından sonucu tek değer olarak döndürür"""
    if isinstance(hir, AssignmentHirLine):
        return hir.value
    elif isinstance(hir, ArithmeticOpHirLine):
        return f"{hir.left_operand} {hir.operator} {hir.right_operand}"
    elif isinstance(hir, ConditionalOpHirLine):
        return f"{hir.left_operand} {hir.operator} {hir.right_operand}"
    else:
        raise Exception("Unsupported temp producer")

def optimize_hir(hir_lines:list[str], symbol_table: SymbolTable) -> list[HirLine]:
    parsed_hir_lines = HirLine.parse_hir_lines(hir_lines)
    optimize_hir_lines = []
    static_vars = find_static_vars(parsed_hir_lines, symbol_table)
    optimized_hir_lines = paste_static_vars(parsed_hir_lines, static_vars)
    optimized_hir_lines = remove_unused_temporaries(optimized_hir_lines)
    print(static_vars)
    return optimized_hir_lines

