from __future__ import annotations

from entities.HirLine import *
from entities.LirLine import *

LOAD_IMM_REGISTER = 'RA'
LOAD_MEM_TEMP_REGISTER = 'RB'

def generate_ir_low(hir_lines:list[HirLine]) -> list[LirLine]:
    low_ir_lines:list[LirLine] = []
    for hir in hir_lines:
        if isinstance(hir, AssignmentHirLine):
            # b = 50 -> LDI 50; STORE b
            if hir.isConstant:
                # Set MAR to variable address
                mar_destination = MovDestination(MovDestinationType.VARIABLE_ADDRESS, hir.var_name)
                low_ir_lines.append(SetMarLirLine.create_line(mar_destination))
                # Load immediate value into register RA
                low_ir_lines.append(LoadImmLirLine.create_line(hir.value))
                mov_destination = MovDestination(MovDestinationType.VARIABLE, hir.var_name)
                mov_source = MovSource(MovSourceType.REGISTER, LOAD_IMM_REGISTER)
                low_ir_lines.append(MovLirLine.create_line(mov_destination, mov_source))
            else: # b = a;
                # Load from a
                source_var_name = hir.value
                mar_destination = MovDestination(MovDestinationType.VARIABLE_ADDRESS, source_var_name) 
                low_ir_lines.append(SetMarLirLine.create_line(mar_destination)) 
                # Load value into register
                mov_source = MovSource(MovSourceType.VARIABLE, source_var_name)
                mov_destination = MovDestination(MovDestinationType.REGISTER, LOAD_MEM_TEMP_REGISTER)
                low_ir_lines.append(MovLirLine.create_line(mov_destination, mov_source))
                # Store into b
                mar_destination = MovDestination(MovDestinationType.VARIABLE_ADDRESS, hir.var_name)
                low_ir_lines.append(SetMarLirLine.create_line(mar_destination))
                mov_source = MovSource(MovSourceType.REGISTER, LOAD_MEM_TEMP_REGISTER)
                mov_destination = MovDestination(MovDestinationType.VARIABLE, hir.var_name)
                low_ir_lines.append(MovLirLine.create_line(mov_destination, mov_source))
        else:
            raise NotImplementedError(f"LIR generation for {type(hir)} is not implemented.")
    return low_ir_lines

if __name__ == '__main__':
    test_hir_lines = [
        "b = 50"
    ]

    hir_lines = HirLine.parse_hir_lines(test_hir_lines)
    lir_lines = generate_ir_low(hir_lines)
    for lir in lir_lines:
        print(lir)
        