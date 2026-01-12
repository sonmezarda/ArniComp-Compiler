from __future__ import annotations
from entities.LirLine import LirLine, SetMarLirLine

def remove_unnecessary_setmars(lir_lines:list[LirLine]) -> list[LirLine]:
    optimized_lir_lines = []
    current_mar_str = "0000"

    for lir in lir_lines:
        if isinstance(lir, SetMarLirLine):
            if lir.destination_str == current_mar_str:
                continue
            else:
                current_mar_str = lir.destination_str
        optimized_lir_lines.append(lir)

    return optimized_lir_lines

def optimize_lir(lir_lines:list[LirLine]) -> list[LirLine]:
    optimized_lir_lines = remove_unnecessary_setmars(lir_lines)
    return optimized_lir_lines