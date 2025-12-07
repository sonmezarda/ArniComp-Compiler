from __future__ import annotations

from entities.HirLine import *
from entities.LirLine import *

def generate_ir_low(hir_lines:list[HirLine]) -> list[str]:
    low_ir_lines:list[LirLine] = []
    for hir in hir_lines:
        if isinstance(hir, AssignmentHirLine):
            # b = 50 -> LDI 50; STORE b
            if hir.isConstant:
                low_ir_lines.append(LoadImmLirLine.create_line(hir.value))
                mov_destination = MovDestination(MovDestinationType.VARIABLE, hir.var_name)
                mov_source = MovSource(MovSourceType.REGISTER, SOURCE_REGISTERS_STR[0])
                low_ir_lines.append(MovLirLine.create_line(mov_destination, mov_source))
    return low_ir_lines

if __name__ == '__main__':
    test_hir_lines = [
        "b = 50"
    ]

    hir_lines = HirLine.parse_hir_lines(test_hir_lines)
    lir_lines = generate_ir_low(hir_lines)
    for lir in lir_lines:
        print(lir)
        