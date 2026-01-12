from __future__ import annotations
from entities.LirLine import LirLine, SetMarLirLine, SetPrLirLine, LabelLirLine

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


def remove_unnecessary_setprs(lir_lines:list[LirLine]) -> list[LirLine]:
    """
    Remove redundant SETPR instructions when PR already points to the target label.
    Also invalidates PR tracking when a label is encountered (since we jumped here
    from somewhere else, PR state is unknown).
    """
    optimized_lir_lines = []
    current_pr_label = None

    for lir in lir_lines:
        if isinstance(lir, SetPrLirLine):
            if lir.target_label == current_pr_label:
                # PR already set to this label, skip
                continue
            else:
                current_pr_label = lir.target_label
        elif isinstance(lir, LabelLirLine):
            # When we reach a label, PR state becomes unknown
            # (we might have jumped here from anywhere)
            current_pr_label = None
        
        optimized_lir_lines.append(lir)

    return optimized_lir_lines


def optimize_lir(lir_lines:list[LirLine]) -> list[LirLine]:
    optimized_lir_lines = remove_unnecessary_setmars(lir_lines)
    optimized_lir_lines = remove_unnecessary_setprs(optimized_lir_lines)
    return optimized_lir_lines