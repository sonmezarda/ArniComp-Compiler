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
        if isinstance(hir, AssignmentHirLine):
            if hir.var_name.startswith('.t'):
                if used_temps_count.get(hir.var_name, 0) == 2:
                    if hir_lines[i+1].type in [HirLineType.ASSIGNMENT]:
                        next_hir : AssignmentHirLine = hir_lines[i+1]
                        hir : AssignmentHirLine = hir
                        optimized_hir_lines.append(AssignmentHirLine(f"{next_hir.var_name} = {hir.value}"))
                        is_next_to_remove = True
                        continue


        optimized_hir_lines.append(hir)
    return  optimized_hir_lines

def propagate_constants(hir_lines: list[HirLine], symbol_table: SymbolTable) -> list[HirLine]:
    """
    Forward constant propagation: Tracks known values of variables at each statement.
    If a variable is assigned a constant and is not volatile, that constant is
    substituted into subsequent uses. If the variable is reassigned, tracking
    continues with the new value.
    """
    propagated_lines: list[HirLine] = []
    
    # Current known value for each variable (None = unknown/dynamic)
    known_values: dict[str, int | None] = {}
    
    for hir in hir_lines:
        if isinstance(hir, AssignmentHirLine):
            var_symbol = symbol_table.get(hir.var_name)
            is_volatile = var_symbol is not None and var_symbol.qualifier == 'volatile'
            
            # First resolve the RHS value (perform propagation)
            resolved_value = _resolve_value(hir.value, known_values)
            
            # If the value was resolved/changed, update the HIR line
            if resolved_value != hir.value:
                hir.set_value(resolved_value, is_constant=isinstance(resolved_value, int))
            
            # Record the new value for the LHS variable (if not volatile)
            if not is_volatile:
                if isinstance(resolved_value, int):
                    known_values[hir.var_name] = resolved_value
                else:
                    # A dynamic value was assigned; we no longer know the value
                    known_values[hir.var_name] = None
            
            # We could remove assignments for non-volatile variables when their value
            # is known and they are not used later. For now we only perform propagation.
            propagated_lines.append(hir)
            
        elif isinstance(hir, ArithmeticOpHirLine):
            # Resolve left and right operands
            resolved_left = _resolve_value(hir.left_operand, known_values)
            resolved_right = _resolve_value(hir.right_operand, known_values)
            
            if resolved_left != hir.left_operand:
                hir.set_left_operand(resolved_left)
            if resolved_right != hir.right_operand:
                hir.set_right_operand(resolved_right)
            
            # Compute the result value if both operands are constant.
            # Note: ArithmeticOpHirLine.evaluate_if_possible() will already do
            # this conversion to AssignmentHirLine; handle that case below.
            if isinstance(hir, AssignmentHirLine):
                # It may have been converted to AssignmentHirLine after evaluation
                known_values[hir.var_name] = hir.value if isinstance(hir.value, int) else None
            else:
                # Result is dynamic/unknown
                known_values[hir.result_var] = None
            
            propagated_lines.append(hir)
            
        elif isinstance(hir, ConditionalOpHirLine):
            # Resolve left and right operands
            resolved_left = _resolve_value(hir.left_operand, known_values)
            resolved_right = _resolve_value(hir.right_operand, known_values)
            
            if resolved_left != hir.left_operand:
                hir.set_left_operand(resolved_left)
            if resolved_right != hir.right_operand:
                hir.set_right_operand(resolved_right)
            
            # Result variable becomes dynamic (unknown)
            known_values[hir.result_var] = None
            propagated_lines.append(hir)
            
        elif isinstance(hir, IfOpHirLine):
            # For IF lines we can also try to resolve the condition variable
            resolved_cond = _resolve_value(hir.cond_var, known_values)
            if resolved_cond != hir.cond_var:
                hir.set_cond_var(resolved_cond)
            propagated_lines.append(hir)
            
        elif isinstance(hir, LabelHirLine):
            # Nothing to do for labels here.
            # NOTE: In a full control-flow analysis we would clear or merge
            # known_values at label boundaries; for simple cases we skip that.
            propagated_lines.append(hir)
            
        else:
            propagated_lines.append(hir)
    
    return propagated_lines


def _resolve_value(value, known_values: dict[str, int | None]):
    """
    Resolve a value: if the value is a variable and a known constant exists,
    return that constant. Otherwise return the value unchanged.
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # Değişken mi kontrol et
        if value in known_values and known_values[value] is not None:
            return known_values[value]
    return value


def remove_dead_assignments(hir_lines: list[HirLine], symbol_table: SymbolTable) -> list[HirLine]:
    """
    Remove dead assignments for non-volatile variables.
    If a variable is assigned and then reassigned without being used in-between,
    the earlier assignment is dead and can be removed.
    """
    # Track the index of the last assignment for each variable
    last_assignment_idx: dict[str, int] = {}
    # Set of variables that are used
    used_vars: set[str] = set()
    # Indices of dead lines
    dead_indices: set[int] = set()
    
    # First pass: determine which variables are used and where assignments occur
    for i, hir in enumerate(hir_lines):
        if isinstance(hir, AssignmentHirLine):
            var_symbol = symbol_table.get(hir.var_name)
            is_volatile = var_symbol is not None and var_symbol.qualifier == 'volatile'
            
            # Mark RHS variable as used
            if isinstance(hir.value, str) and not hir.value.isdigit():
                used_vars.add(hir.value)
            
            if not is_volatile:
                # If this variable was assigned before and not used in the meantime,
                # the previous assignment is dead
                if hir.var_name in last_assignment_idx:
                    if hir.var_name not in used_vars:
                        dead_indices.add(last_assignment_idx[hir.var_name])
                # Record this assignment and clear usage mark
                last_assignment_idx[hir.var_name] = i
                used_vars.discard(hir.var_name)
                
        elif isinstance(hir, ArithmeticOpHirLine):
            # Mark operands as used
            if isinstance(hir.left_operand, str):
                used_vars.add(hir.left_operand)
            if isinstance(hir.right_operand, str):
                used_vars.add(hir.right_operand)
            # Apply same logic for the result variable
            if hir.result_var in last_assignment_idx:
                if hir.result_var not in used_vars:
                    dead_indices.add(last_assignment_idx[hir.result_var])
            last_assignment_idx[hir.result_var] = i
            used_vars.discard(hir.result_var)
            
        elif isinstance(hir, ConditionalOpHirLine):
            if isinstance(hir.left_operand, str):
                used_vars.add(hir.left_operand)
            if isinstance(hir.right_operand, str):
                used_vars.add(hir.right_operand)
            if hir.result_var in last_assignment_idx:
                if hir.result_var not in used_vars:
                    dead_indices.add(last_assignment_idx[hir.result_var])
            last_assignment_idx[hir.result_var] = i
            used_vars.discard(hir.result_var)
            
        elif isinstance(hir, IfOpHirLine):
            if isinstance(hir.cond_var, str):
                used_vars.add(hir.cond_var)
    
    # After the loop, any last assignments that were never used are dead
    # (for non-volatile variables)
    for var_name, idx in last_assignment_idx.items():
        if var_name not in used_vars:
            # This variable was never used after its last assignment
            var_symbol = symbol_table.get(var_name)
            is_volatile = var_symbol is not None and var_symbol.qualifier == 'volatile'
            if not is_volatile:
                dead_indices.add(idx)
    
    # Build the new list by removing dead lines
    return [hir for i, hir in enumerate(hir_lines) if i not in dead_indices]

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
    """Return the single result value produced by a producer line."""
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
    
    # Forward constant propagation: substitute known values at each statement
    optimized_hir_lines = propagate_constants(parsed_hir_lines, symbol_table)
    
    # Remove unused assignments (dead code elimination)
    optimized_hir_lines = remove_dead_assignments(optimized_hir_lines, symbol_table)
    
    # Temporary variable optimizations
    optimized_hir_lines = remove_unused_temporaries(optimized_hir_lines)
    
    return optimized_hir_lines

