from __future__ import annotations

from entities.HirLine import *
from entities.LirLine import *

LOAD_IMM_REGISTER = 'RA'
LOAD_MEM_TEMP_REGISTER = 'RB'
_internal_label_counter = 0
_software_temp_counter = 0

# Map HIR comparison operators to LIR conditional jump types
COMPARISON_TO_JUMP = {
    '<': 'JLT',
    '<=': 'JLE',
    '>': 'JGT',
    '>=': 'JGE',
    '==': 'JEQ',
    '!=': 'JNE',
}


def _new_internal_label(prefix: str = "Ltmp") -> str:
    global _internal_label_counter
    label = f".L{prefix}{_internal_label_counter}"
    _internal_label_counter += 1
    return label


def _new_software_temp(prefix: str = "tmp") -> str:
    global _software_temp_counter
    name = f".t{prefix}{_software_temp_counter}"
    _software_temp_counter += 1
    return name

def generate_ir_low(hir_lines:list[HirLine]) -> list[LirLine]:
    low_ir_lines:list[LirLine] = []
    temp_registers: dict[str, str] = {}

    for hir in hir_lines:
        if isinstance(hir, AssignmentHirLine):
            # b = 50 -> LDI 50; STORE b
            if hir.isConstant:
                value = int(hir.value) & 0xFF
                # Set MAR to variable address
                mar_destination = MovDestination(MovDestinationType.VARIABLE_ADDRESS, hir.var_name)
                low_ir_lines.append(SetMarLirLine.create_line(mar_destination))
                # Load immediate value into register RA
                low_ir_lines.append(LoadImmLirLine.create_line(value))
                mov_destination = MovDestination(MovDestinationType.VARIABLE, hir.var_name)
                mov_source = MovSource(MovSourceType.REGISTER, LOAD_IMM_REGISTER)
                low_ir_lines.append(MovLirLine.create_line(mov_destination, mov_source))
            else: # b = a;
                # Load from a
                source_var_name = hir.value
                if not isinstance(source_var_name, str):
                    raise ValueError(f"Expected variable source name, got '{source_var_name}'")
                mar_destination = MovDestination(MovDestinationType.VARIABLE_ADDRESS, source_var_name)
                low_ir_lines.append(SetMarLirLine.create_line(mar_destination))
                # Load value into register
                mov_source = MovSource(MovSourceType.VARIABLE, source_var_name)
                mov_destination = MovDestination(MovDestinationType.REGISTER, LOAD_MEM_TEMP_REGISTER)
                low_ir_lines.append(MovLirLine.create_line(mov_destination, mov_source))
                mov_source = MovSource(MovSourceType.REGISTER, LOAD_MEM_TEMP_REGISTER)

                # Store into b
                mar_destination = MovDestination(MovDestinationType.VARIABLE_ADDRESS, hir.var_name)
                low_ir_lines.append(SetMarLirLine.create_line(mar_destination))
                mov_destination = MovDestination(MovDestinationType.VARIABLE, hir.var_name)
                low_ir_lines.append(MovLirLine.create_line(mov_destination, mov_source))
                
        elif isinstance(hir, ArithmeticOpHirLine):
            low_ir_lines.extend(_generate_arithmetic_lir(hir, temp_registers))

        elif isinstance(hir, UnaryOpHirLine):
            low_ir_lines.extend(_generate_unary_lir(hir, temp_registers))

        elif isinstance(hir, CallHirLine):
            raise NotImplementedError("CALL lowering is not implemented in LIR generation yet.")

        elif isinstance(hir, IfOpHirLine):
            # IF left op right GOTO label
            # Generate: load left into RD, load right into RA, CMP RA, SETPR label, conditional jump
            temp_registers.clear()
            low_ir_lines.extend(_generate_if_lir(hir))
            
        elif isinstance(hir, GotoHirLine):
            # GOTO label -> SETPR label; GOTO
            temp_registers.clear()
            low_ir_lines.append(SetPrLirLine.create_line(hir.target_label))
            low_ir_lines.append(GotoLirLine.create_line())
            
        elif isinstance(hir, LabelHirLine):
            # label:
            temp_registers.clear()
            low_ir_lines.append(LabelLirLine.create_line(hir.label_name))
            
        elif isinstance(hir, ConditionalOpHirLine):
            low_ir_lines.extend(_generate_conditional_lir(hir, temp_registers))
        else:
            raise NotImplementedError(f"LIR generation for {type(hir)} is not implemented.")

        # Any real variable assignment invalidates temp alias with same name.
        if isinstance(hir, (AssignmentHirLine, ArithmeticOpHirLine, UnaryOpHirLine)):
            if hasattr(hir, 'var_name') and hir.var_name in temp_registers:
                del temp_registers[hir.var_name]
            if hasattr(hir, 'result_var') and hir.result_var in temp_registers and not hir.result_var.startswith('.t'):
                del temp_registers[hir.result_var]

    return low_ir_lines


def _load_operand_into_register(
    lines: list[LirLine],
    operand: int | str,
    is_constant: bool,
    target_reg: str,
    _temp_registers: dict[str, str],
):
    if is_constant:
        value = int(operand) & 0xFF
        lines.append(LoadImmLirLine.create_line(value))
        if target_reg != 'RA':
            lines.append(MovLirLine.create_line(
                MovDestination(MovDestinationType.REGISTER, target_reg),
                MovSource(MovSourceType.REGISTER, 'RA')
            ))
        return

    if not isinstance(operand, str):
        raise ValueError(f"Expected variable operand as string, got '{operand}'")
    mar_dest = MovDestination(MovDestinationType.VARIABLE_ADDRESS, operand)
    lines.append(SetMarLirLine.create_line(mar_dest))
    lines.append(MovLirLine.create_line(
        MovDestination(MovDestinationType.REGISTER, target_reg),
        MovSource(MovSourceType.VARIABLE, operand)
    ))


def _build_source_for_operand(
    lines: list[LirLine],
    operand: int | str,
    is_constant: bool,
    _temp_registers: dict[str, str],
) -> MovSource:
    if is_constant:
        value = int(operand) & 0xFF
        lines.append(LoadImmLirLine.create_line(value))
        return MovSource(MovSourceType.REGISTER, 'RA')

    if not isinstance(operand, str):
        raise ValueError(f"Expected variable operand as string, got '{operand}'")
    mar_dest = MovDestination(MovDestinationType.VARIABLE_ADDRESS, operand)
    lines.append(SetMarLirLine.create_line(mar_dest))
    return MovSource(MovSourceType.VARIABLE, operand)


def _store_acc_result(
    lines: list[LirLine],
    destination_var: str,
    temp_registers: dict[str, str],
):
    _store_result_from_register(lines, destination_var, "ACC", temp_registers)


def _store_result_from_register(
    lines: list[LirLine],
    destination_var: str,
    source_reg: str,
    _temp_registers: dict[str, str],
):
    # SETMAR generation may clobber RA (via LDI), so preserve it first.
    safe_source_reg = source_reg
    if source_reg == 'RA':
        lines.append(MovLirLine.create_line(
            MovDestination(MovDestinationType.REGISTER, 'RB'),
            MovSource(MovSourceType.REGISTER, 'RA')
        ))
        safe_source_reg = 'RB'

    mar_dest = MovDestination(MovDestinationType.VARIABLE_ADDRESS, destination_var)
    lines.append(SetMarLirLine.create_line(mar_dest))
    lines.append(MovLirLine.create_line(
        MovDestination(MovDestinationType.VARIABLE, destination_var),
        MovSource(MovSourceType.REGISTER, safe_source_reg)
    ))


def _emit_bool_from_current_flags(
    lines: list[LirLine],
    true_jump_type: str,
    destination_var: str,
    temp_registers: dict[str, str],
) -> None:
    """
    Store boolean result (0/1) into destination_var based on current flags.
    If true_jump_type condition holds => 1, else 0.
    """
    true_label = _new_internal_label("cond_true")
    end_label = _new_internal_label("cond_end")

    # Default false -> RB = 0
    lines.append(LoadImmLirLine.create_line(0))
    lines.append(MovLirLine.create_line(
        MovDestination(MovDestinationType.REGISTER, 'RB'),
        MovSource(MovSourceType.REGISTER, 'RA')
    ))

    lines.append(SetPrLirLine.create_line(true_label))
    lines.append(ConditionalJumpLirLine.create_line(true_jump_type))
    lines.append(SetPrLirLine.create_line(end_label))
    lines.append(GotoLirLine.create_line())

    # True -> RB = 1
    lines.append(LabelLirLine.create_line(true_label))
    lines.append(LoadImmLirLine.create_line(1))
    lines.append(MovLirLine.create_line(
        MovDestination(MovDestinationType.REGISTER, 'RB'),
        MovSource(MovSourceType.REGISTER, 'RA')
    ))
    lines.append(LabelLirLine.create_line(end_label))

    _store_result_from_register(lines, destination_var, 'RB', temp_registers)


def _emit_compare(
    lines: list[LirLine],
    left_operand: int | str,
    left_is_constant: bool,
    right_operand: int | str,
    right_is_constant: bool,
    temp_registers: dict[str, str],
) -> None:
    _load_operand_into_register(lines, left_operand, left_is_constant, 'RD', temp_registers)
    if right_is_constant:
        lines.append(LoadImmLirLine.create_line(int(right_operand) & 0xFF))
        lines.append(CmpLirLine.create_line(MovSource(MovSourceType.REGISTER, 'RA')))
        return

    if not isinstance(right_operand, str):
        raise ValueError(f"Expected variable on right operand, got '{right_operand}'")
    mar_dest = MovDestination(MovDestinationType.VARIABLE_ADDRESS, right_operand)
    lines.append(SetMarLirLine.create_line(mar_dest))
    lines.append(CmpLirLine.create_line(MovSource(MovSourceType.VARIABLE, right_operand)))


def _emit_truthy_register(
    lines: list[LirLine],
    operand: int | str,
    is_constant: bool,
    target_reg: str,
    temp_registers: dict[str, str],
) -> None:
    """
    Convert operand to bool (0/1) and write into target_reg.
    """
    _load_operand_into_register(lines, operand, is_constant, 'RD', temp_registers)
    lines.append(LoadImmLirLine.create_line(0))
    lines.append(CmpLirLine.create_line(MovSource(MovSourceType.REGISTER, 'RA')))

    true_label = _new_internal_label("truthy_true")
    end_label = _new_internal_label("truthy_end")

    lines.append(LoadImmLirLine.create_line(0))
    lines.append(MovLirLine.create_line(
        MovDestination(MovDestinationType.REGISTER, target_reg),
        MovSource(MovSourceType.REGISTER, 'RA')
    ))
    lines.append(SetPrLirLine.create_line(true_label))
    lines.append(ConditionalJumpLirLine.create_line('JNE'))
    lines.append(SetPrLirLine.create_line(end_label))
    lines.append(GotoLirLine.create_line())
    lines.append(LabelLirLine.create_line(true_label))
    lines.append(LoadImmLirLine.create_line(1))
    lines.append(MovLirLine.create_line(
        MovDestination(MovDestinationType.REGISTER, target_reg),
        MovSource(MovSourceType.REGISTER, 'RA')
    ))
    lines.append(LabelLirLine.create_line(end_label))


def _generate_conditional_lir(hir: ConditionalOpHirLine, temp_registers: dict[str, str]) -> list[LirLine]:
    lines: list[LirLine] = []
    operator = hir.operator

    if operator in COMPARISON_TO_JUMP:
        _emit_compare(
            lines,
            hir.left_operand,
            hir.left_isConstant,
            hir.right_operand,
            hir.right_isConstant,
            temp_registers,
        )
        _emit_bool_from_current_flags(lines, COMPARISON_TO_JUMP[operator], hir.result_var, temp_registers)
        return lines

    if operator == '&&':
        _emit_truthy_register(lines, hir.left_operand, hir.left_isConstant, 'RB', temp_registers)
        _emit_truthy_register(lines, hir.right_operand, hir.right_isConstant, 'RD', temp_registers)
        lines.append(AluOpLirLine.create_line('AND', MovSource(MovSourceType.REGISTER, 'RB')))
        _store_acc_result(lines, hir.result_var, temp_registers)
        return lines

    if operator == '||':
        _emit_truthy_register(lines, hir.left_operand, hir.left_isConstant, 'RB', temp_registers)
        _emit_truthy_register(lines, hir.right_operand, hir.right_isConstant, 'RD', temp_registers)

        # sum = left_bool + right_bool
        lines.append(AluOpLirLine.create_line('ADD', MovSource(MovSourceType.REGISTER, 'RB')))

        # Convert sum != 0 to bool
        lines.append(MovLirLine.create_line(
            MovDestination(MovDestinationType.REGISTER, 'RD'),
            MovSource(MovSourceType.REGISTER, 'ACC')
        ))
        lines.append(LoadImmLirLine.create_line(0))
        lines.append(CmpLirLine.create_line(MovSource(MovSourceType.REGISTER, 'RA')))
        _emit_bool_from_current_flags(lines, 'JNE', hir.result_var, temp_registers)
        return lines

    raise NotImplementedError(f"Conditional operator '{operator}' is not supported in LIR lowering yet.")


def _generate_arithmetic_lir(hir: ArithmeticOpHirLine, temp_registers: dict[str, str]) -> list[LirLine]:
    op_map = {
        '+': 'ADD',
        '-': 'SUB',
        '&': 'AND',
        '^': 'XOR',
    }
    opcode = op_map.get(hir.operator)
    if opcode is not None:
        lines: list[LirLine] = []
        _load_operand_into_register(lines, hir.left_operand, hir.left_isConstant, 'RD', temp_registers)
        source = _build_source_for_operand(lines, hir.right_operand, hir.right_isConstant, temp_registers)
        lines.append(AluOpLirLine.create_line(opcode, source))
        _store_acc_result(lines, hir.result_var, temp_registers)
        return lines

    if hir.operator == '|':
        return _generate_or_lir(hir, temp_registers)

    if hir.operator == '<<':
        if hir.right_isConstant:
            return _generate_shift_left_const_lir(hir, temp_registers)
        return _generate_shift_left_variable_lir(hir, temp_registers)

    raise NotImplementedError(f"Arithmetic operator '{hir.operator}' is not supported in LIR lowering yet.")


def _generate_or_lir(hir: ArithmeticOpHirLine, temp_registers: dict[str, str]) -> list[LirLine]:
    """
    OR synthesis using De Morgan:
      A | B = NOT( NOT(A) AND NOT(B) )
    """
    lines: list[LirLine] = []
    _load_operand_into_register(lines, hir.left_operand, hir.left_isConstant, 'RD', temp_registers)
    lines.append(AluOpLirLine.create_line('NOT', MovSource(MovSourceType.REGISTER, 'RD')))
    lines.append(MovLirLine.create_line(
        MovDestination(MovDestinationType.REGISTER, 'RB'),
        MovSource(MovSourceType.REGISTER, 'ACC')
    ))

    source_b = _build_source_for_operand(lines, hir.right_operand, hir.right_isConstant, temp_registers)
    lines.append(AluOpLirLine.create_line('NOT', source_b))
    lines.append(MovLirLine.create_line(
        MovDestination(MovDestinationType.REGISTER, 'RA'),
        MovSource(MovSourceType.REGISTER, 'ACC')
    ))

    lines.append(MovLirLine.create_line(
        MovDestination(MovDestinationType.REGISTER, 'RD'),
        MovSource(MovSourceType.REGISTER, 'RB')
    ))
    lines.append(AluOpLirLine.create_line('AND', MovSource(MovSourceType.REGISTER, 'RA')))
    lines.append(AluOpLirLine.create_line('NOT', MovSource(MovSourceType.REGISTER, 'ACC')))
    _store_acc_result(lines, hir.result_var, temp_registers)
    return lines


def _generate_shift_left_const_lir(hir: ArithmeticOpHirLine, temp_registers: dict[str, str]) -> list[LirLine]:
    """
    x << n  -> repeated doubling with ADD RD.
    """
    lines: list[LirLine] = []
    shift_count = int(hir.right_operand)
    if shift_count < 0:
        raise NotImplementedError("Negative shift-left is not supported.")

    _load_operand_into_register(lines, hir.left_operand, hir.left_isConstant, 'RD', temp_registers)

    if shift_count == 0:
        _store_result_from_register(lines, hir.result_var, 'RD', temp_registers)
        return lines

    for i in range(shift_count):
        lines.append(AluOpLirLine.create_line('ADD', MovSource(MovSourceType.REGISTER, 'RD')))
        if i != shift_count - 1:
            lines.append(MovLirLine.create_line(
                MovDestination(MovDestinationType.REGISTER, 'RD'),
                MovSource(MovSourceType.REGISTER, 'ACC')
            ))

    _store_acc_result(lines, hir.result_var, temp_registers)
    return lines


def _generate_shift_left_variable_lir(hir: ArithmeticOpHirLine, temp_registers: dict[str, str]) -> list[LirLine]:
    """
    x << n (runtime n) using loop:
      result = x
      count = n
      while count > 0:
          result = result + result
          count = count - 1
    """
    lines: list[LirLine] = []
    result_temp = _new_software_temp("shl_res")
    count_temp = _new_software_temp("shl_cnt")
    loop_label = _new_internal_label("shl_loop")
    end_label = _new_internal_label("shl_end")

    # result_temp = left operand
    _load_operand_into_register(lines, hir.left_operand, hir.left_isConstant, 'RB', temp_registers)
    _store_result_from_register(lines, result_temp, 'RB', temp_registers)

    # count_temp = right operand
    _load_operand_into_register(lines, hir.right_operand, hir.right_isConstant, 'RB', temp_registers)
    _store_result_from_register(lines, count_temp, 'RB', temp_registers)

    lines.append(LabelLirLine.create_line(loop_label))

    # if count <= 0 goto end
    lines.append(SetMarLirLine.create_line(MovDestination(MovDestinationType.VARIABLE_ADDRESS, count_temp)))
    lines.append(MovLirLine.create_line(
        MovDestination(MovDestinationType.REGISTER, 'RD'),
        MovSource(MovSourceType.VARIABLE, count_temp)
    ))
    lines.append(LoadImmLirLine.create_line(0))
    lines.append(CmpLirLine.create_line(MovSource(MovSourceType.REGISTER, 'RA')))
    lines.append(SetPrLirLine.create_line(end_label))
    lines.append(ConditionalJumpLirLine.create_line('JLE'))

    # result = result + result
    lines.append(SetMarLirLine.create_line(MovDestination(MovDestinationType.VARIABLE_ADDRESS, result_temp)))
    lines.append(MovLirLine.create_line(
        MovDestination(MovDestinationType.REGISTER, 'RD'),
        MovSource(MovSourceType.VARIABLE, result_temp)
    ))
    lines.append(AluOpLirLine.create_line('ADD', MovSource(MovSourceType.REGISTER, 'RD')))
    _store_result_from_register(lines, result_temp, 'ACC', temp_registers)

    # count = count - 1
    lines.append(SetMarLirLine.create_line(MovDestination(MovDestinationType.VARIABLE_ADDRESS, count_temp)))
    lines.append(MovLirLine.create_line(
        MovDestination(MovDestinationType.REGISTER, 'RD'),
        MovSource(MovSourceType.VARIABLE, count_temp)
    ))
    lines.append(LoadImmLirLine.create_line(1))
    lines.append(AluOpLirLine.create_line('SUB', MovSource(MovSourceType.REGISTER, 'RA')))
    _store_result_from_register(lines, count_temp, 'ACC', temp_registers)

    lines.append(SetPrLirLine.create_line(loop_label))
    lines.append(GotoLirLine.create_line())
    lines.append(LabelLirLine.create_line(end_label))

    # final store
    lines.append(SetMarLirLine.create_line(MovDestination(MovDestinationType.VARIABLE_ADDRESS, result_temp)))
    lines.append(MovLirLine.create_line(
        MovDestination(MovDestinationType.REGISTER, 'RB'),
        MovSource(MovSourceType.VARIABLE, result_temp)
    ))
    _store_result_from_register(lines, hir.result_var, 'RB', temp_registers)
    return lines


def _generate_unary_lir(hir: UnaryOpHirLine, temp_registers: dict[str, str]) -> list[LirLine]:
    lines: list[LirLine] = []

    if hir.operator == 'bitnot':
        source = _build_source_for_operand(lines, hir.operand, hir.isConstant, temp_registers)
        lines.append(AluOpLirLine.create_line('NOT', source))
    elif hir.operator == 'neg':
        lines.append(LoadImmLirLine.create_line(0))
        lines.append(MovLirLine.create_line(
            MovDestination(MovDestinationType.REGISTER, 'RD'),
            MovSource(MovSourceType.REGISTER, 'RA')
        ))
        source = _build_source_for_operand(lines, hir.operand, hir.isConstant, temp_registers)
        lines.append(AluOpLirLine.create_line('SUB', source))
    elif hir.operator == 'not':
        _load_operand_into_register(lines, hir.operand, hir.isConstant, 'RD', temp_registers)
        lines.append(LoadImmLirLine.create_line(0))
        lines.append(CmpLirLine.create_line(MovSource(MovSourceType.REGISTER, 'RA')))

        true_label = _new_internal_label("not_true")
        end_label = _new_internal_label("not_end")

        # Keep result in RB so SETPR (which uses RA in asm backend) cannot clobber it.
        lines.append(LoadImmLirLine.create_line(0))
        lines.append(MovLirLine.create_line(
            MovDestination(MovDestinationType.REGISTER, 'RB'),
            MovSource(MovSourceType.REGISTER, 'RA')
        ))
        lines.append(SetPrLirLine.create_line(true_label))
        lines.append(ConditionalJumpLirLine.create_line('JEQ'))
        lines.append(SetPrLirLine.create_line(end_label))
        lines.append(GotoLirLine.create_line())
        lines.append(LabelLirLine.create_line(true_label))
        lines.append(LoadImmLirLine.create_line(1))
        lines.append(MovLirLine.create_line(
            MovDestination(MovDestinationType.REGISTER, 'RB'),
            MovSource(MovSourceType.REGISTER, 'RA')
        ))
        lines.append(LabelLirLine.create_line(end_label))
        _store_result_from_register(lines, hir.result_var, 'RB', temp_registers)
        return lines
    else:
        raise NotImplementedError(f"Unary operator '{hir.operator}' is not supported in LIR lowering.")

    _store_acc_result(lines, hir.result_var, temp_registers)
    return lines


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
        if not isinstance(left, int):
            left = int(left)
        lines.append(LoadImmLirLine.create_line(left))
        lines.append(MovLirLine.create_line(
            MovDestination(MovDestinationType.REGISTER, 'RD'),
            MovSource(MovSourceType.REGISTER, 'RA')
        ))
    else:
        if not isinstance(left, str):
            raise ValueError(f"Expected variable on IF left operand, got '{left}'")
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
        if not isinstance(right, int):
            right = int(right)
        lines.append(LoadImmLirLine.create_line(right))
        lines.append(CmpLirLine.create_line(MovSource(MovSourceType.REGISTER, 'RA')))
    else:
        if not isinstance(right, str):
            raise ValueError(f"Expected variable on IF right operand, got '{right}'")
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
        
