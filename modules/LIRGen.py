from __future__ import annotations

from entities.HirLine import *
from entities.LirLine import *

LOAD_IMM_REGISTER = 'RA'
LOAD_MEM_TEMP_REGISTER = 'RB'

# Map HIR comparison operators to LIR conditional jump types
COMPARISON_TO_JUMP = {
    '<': 'JLT',
    '<=': 'JLE',
    '>': 'JGT',
    '>=': 'JGE',
    '==': 'JEQ',
    '!=': 'JNE',
}

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
                
        elif isinstance(hir, IfOpHirLine):
            # IF left op right GOTO label
            # Generate: load left into RD, load right into RA, CMP RA, SETPR label, conditional jump
            low_ir_lines.extend(_generate_if_lir(hir))
            
        elif isinstance(hir, GotoHirLine):
            # GOTO label -> SETPR label; GOTO
            low_ir_lines.append(SetPrLirLine.create_line(hir.target_label))
            low_ir_lines.append(GotoLirLine.create_line())
            
        elif isinstance(hir, LabelHirLine):
            # label:
            low_ir_lines.append(LabelLirLine.create_line(hir.label_name))
            
        elif isinstance(hir, ConditionalOpHirLine):
            destination = hir.result_var
            # if left is var
            if not hir.left_isConstant:
                if hir.right_isConstant:
                    pass
        else:
            raise NotImplementedError(f"LIR generation for {type(hir)} is not implemented.")
    return low_ir_lines


def _generate_if_lir(hir: IfOpHirLine) -> list[LirLine]:
    """
    Generate LIR for IF statement.
    
    For comparison like 'IF a <= 40 GOTO label':
    1. Load left operand into RD
    2. Load right operand into RA (or use M if variable)
    3. CMP RA (or CMP M)
    4. Conditional jump based on operator
    
    Note: CMP compares RD with source. Flags are set based on RD vs source.
    - LT flag: RD < source
    - GT flag: RD > source
    - EQ flag: RD == source
    """
    lines: list[LirLine] = []
    left = hir.left_operand
    right = hir.right_operand
    operator = hir.operator
    target_label = hir.target_label
    
    # Load left operand into RD
    if hir.left_isConstant:
        # LDI left; MOV RD, RA
        lines.append(LoadImmLirLine.create_line(left))
        lines.append(MovLirLine.create_line(
            MovDestination(MovDestinationType.REGISTER, 'RD'),
            MovSource(MovSourceType.REGISTER, 'RA')
        ))
    else:
        # Load from variable: SETMAR var; MOV RD, M
        mar_dest = MovDestination(MovDestinationType.VARIABLE_ADDRESS, left)
        lines.append(SetMarLirLine.create_line(mar_dest))
        lines.append(MovLirLine.create_line(
            MovDestination(MovDestinationType.REGISTER, 'RD'),
            MovSource(MovSourceType.VARIABLE, left)
        ))
    
    # Load right operand and compare
    if hir.right_isConstant:
        # LDI right; CMP RA
        lines.append(LoadImmLirLine.create_line(right))
        lines.append(CmpLirLine.create_line(MovSource(MovSourceType.REGISTER, 'RA')))
    else:
        # SETMAR var; CMP M
        mar_dest = MovDestination(MovDestinationType.VARIABLE_ADDRESS, right)
        lines.append(SetMarLirLine.create_line(mar_dest))
        lines.append(CmpLirLine.create_line(MovSource(MovSourceType.VARIABLE, right)))
    
    # Conditional jump: SETPR label, then jump instruction
    jump_type = COMPARISON_TO_JUMP.get(operator)
    if jump_type is None:
        raise NotImplementedError(f"Comparison operator '{operator}' not supported in LIR")
    
    lines.append(SetPrLirLine.create_line(target_label))
    lines.append(ConditionalJumpLirLine.create_line(jump_type))
    
    return lines

if __name__ == '__main__':
    test_hir_lines = [
        "b = 50"
    ]

    hir_lines = HirLine.parse_hir_lines(test_hir_lines)
    lir_lines = generate_ir_low(hir_lines)
    for lir in lir_lines:
        print(lir)
        