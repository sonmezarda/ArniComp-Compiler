from __future__ import annotations

import re
from helpers.HirHelper import _op_eval


def _try_parse_int_token(value: str | int | object) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    try:
        return int(value, 0)
    except Exception:
        return None


def _is_int_token(value: str | int) -> bool:
    return _try_parse_int_token(value) is not None


def _parse_int_token(value: str | int) -> int:
    parsed = _try_parse_int_token(value)
    if parsed is None:
        raise ValueError(f"Value '{value}' is not a valid integer token.")
    return parsed


class HirLine:
    def __init__(self, line:str):
        self.line = line
        self.splitted = line.split()
        self.splitted_len = len(self.splitted)
        self.type: str | None = None

    def __str__(self):
        return self.line
    

    @staticmethod
    def parse_hir_line(hir_line:str) -> HirLine:
        if re.match(r"^\S+\s*=\s*(neg|bitnot|not)\s+.+$", hir_line):
            return UnaryOpHirLine(hir_line)

        if re.match(r"^\S+\s*=\s*CALL\s+\w+\s*\(.*\)\s*$", hir_line):
            return CallHirLine(hir_line)

        splitted = hir_line.split()
        splitted_len = len(splitted)
        if splitted_len == 3 and splitted[1] == '=':
            return AssignmentHirLine(hir_line)
        elif splitted_len == 5 and splitted[3] in ['+', '-', '*', '/', '%', '<<', '>>', '&', '|', '^']:
            return ArithmeticOpHirLine(hir_line)
        elif splitted_len == 5 and splitted[3] in ['==', '!=', '<', '<=', '>', '>=', '&&', '||']:
            return ConditionalOpHirLine(hir_line)
        elif splitted_len == 6 and splitted[0] == 'IF' and splitted[4] == 'GOTO':
            # New format: IF left op right GOTO label
            return IfOpHirLine(hir_line)
        elif splitted_len == 2 and splitted[0] == 'GOTO':
            return GotoHirLine(hir_line)
        elif splitted_len == 1 and splitted[0].endswith(':'):
            return LabelHirLine(hir_line)
        else:
            raise NotImplementedError(f"HIR line parsing for format '{hir_line}' not implemented.")
        
    @staticmethod
    def parse_hir_lines(hir_lines:list[str]) -> list[HirLine]:
        parsed_lines = []
        for line in hir_lines:
            parsed_line = HirLine.parse_hir_line(line)
            parsed_lines.append(parsed_line)
        return parsed_lines
        


class AssignmentHirLine(HirLine):
    def __init__(self, line:str):
        super().__init__(line)
        self.type = HirLineType.ASSIGNMENT
        self.var_name = self.splitted[0]
        self.value: int | str = self.splitted[2]
        self.isConstant = _is_int_token(self.value)
        if self.isConstant:
            self.value = _parse_int_token(self.value)

    def set_value(self, new_value: int | str, is_constant:bool=False):
        self.value = new_value
        self.isConstant = is_constant
        if self.isConstant:
            parsed = _try_parse_int_token(self.value)
            if parsed is not None:
                self.value = parsed
        self.update_line()

    def update_line(self):
        self.line = f"{self.var_name} = {self.value}"
    
class ArithmeticOpHirLine(HirLine):
    def __init__(self, line:str):
        super().__init__(line)
        self.type = HirLineType.ARITHMETIC_OP
        self.result_var = self.splitted[0]
        self.left_operand: int | str = self.splitted[2]
        self.operator = self.splitted[3]
        self.right_operand: int | str = self.splitted[4]
        self.left_isConstant = False
        self.right_isConstant = False
        self.set_left_operand(self.left_operand)
        self.set_right_operand(self.right_operand)
        if self.left_isConstant:
            self.left_operand = int(self.left_operand)
        if self.right_isConstant:
            self.right_operand = int(self.right_operand)
        
    def set_left_operand(self, new_left: int | str):
        self.left_operand = new_left
        if isinstance(self.left_operand, str):
            self.left_isConstant = _is_int_token(self.left_operand)
            self.left_operand = _parse_int_token(self.left_operand) if self.left_isConstant else self.left_operand
        elif isinstance(self.left_operand, int):
            self.left_isConstant = True
    
        self.evaluate_if_possible()
        self.update_line()

    def set_right_operand(self, new_right: int | str):
        self.right_operand = new_right
        if isinstance(self.right_operand, str):
            self.right_isConstant = _is_int_token(self.right_operand)
            self.right_operand = _parse_int_token(self.right_operand) if self.right_isConstant else self.right_operand
        elif isinstance(self.right_operand, int):
            self.right_isConstant = True
        self.evaluate_if_possible()
        self.update_line()

    def evaluate_if_possible(self):
        if self.left_isConstant and self.right_isConstant:
            print("evaluating", self.left_operand, self.operator, self.right_operand)
            evaluated = _op_eval[self.operator](self.left_operand, self.right_operand)
            print("evaluated to", evaluated)
            new_self = AssignmentHirLine(f"{self.result_var} = {evaluated}")
            self.__class__ = AssignmentHirLine
            self.__dict__ = new_self.__dict__
            new_self.set_value(evaluated)
            
            
    def update_line(self):
        self.line = f"{self.result_var} = {self.left_operand} {self.operator} {self.right_operand}"


class ConditionalOpHirLine(HirLine):
    def __init__(self, line:str):
        super().__init__(line)
        self.type = HirLineType.CONDITIONAL_OP
        self.result_var = self.splitted[0]
        self.left_operand: int | str = self.splitted[2]
        self.operator = self.splitted[3]
        self.right_operand: int | str = self.splitted[4]
        self.left_isConstant = _is_int_token(self.left_operand)
        self.right_isConstant = _is_int_token(self.right_operand)
        if self.left_isConstant:
            self.left_operand = _parse_int_token(self.left_operand)
        if self.right_isConstant:
            self.right_operand = _parse_int_token(self.right_operand)

    def set_left_operand(self, new_left: int | str):
        self.left_operand = new_left
        self.update_line()
        
    def set_right_operand(self, new_right: int | str):
        self.right_operand = new_right
        self.update_line()

    def update_line(self):
        self.line = f"{self.result_var} = {self.left_operand} {self.operator} {self.right_operand}"


class UnaryOpHirLine(HirLine):
    def __init__(self, line: str):
        super().__init__(line)
        self.type = HirLineType.UNARY_OP
        match = re.match(r"^(\S+)\s*=\s*(neg|bitnot|not)\s+(.+)$", line)
        if not match:
            raise ValueError(f"Invalid unary HIR line: {line}")

        self.result_var = match.group(1)
        self.operator = match.group(2)
        self.operand: int | str = match.group(3).strip()
        self.isConstant = _is_int_token(self.operand)
        if self.isConstant:
            self.operand = _parse_int_token(self.operand)

    def set_operand(self, new_operand: int | str):
        self.operand = new_operand
        self.isConstant = _is_int_token(new_operand)
        if self.isConstant and isinstance(self.operand, str):
            self.operand = _parse_int_token(self.operand)
        self.update_line()

    def update_line(self):
        self.line = f"{self.result_var} = {self.operator} {self.operand}"


class CallHirLine(HirLine):
    def __init__(self, line: str):
        super().__init__(line)
        self.type = HirLineType.CALL_OP
        match = re.match(r"^(\S+)\s*=\s*CALL\s+(\w+)\s*\((.*)\)\s*$", line)
        if not match:
            raise ValueError(f"Invalid CALL HIR line: {line}")

        self.result_var = match.group(1)
        self.function_name = match.group(2)
        args_part = match.group(3).strip()
        if args_part == "":
            self.args = []
        else:
            self.args = [arg.strip() for arg in args_part.split(",")]

    def update_line(self):
        self.line = f"{self.result_var} = CALL {self.function_name}({', '.join(self.args)})"


class IfOpHirLine(HirLine):
    """
    Example: IF a <= 40 GOTO .Lelse0
    """
    def __init__(self, line:str):
        super().__init__(line)
        self.type = HirLineType.IF_OP
        # Parse: IF left op right GOTO label
        self.left_operand: int | str = self.splitted[1]
        self.operator = self.splitted[2]
        self.right_operand: int | str = self.splitted[3]
        self.target_label = self.splitted[5]
        
        # Check if operands are constants
        self.left_isConstant = self._is_constant(self.left_operand)
        self.right_isConstant = self._is_constant(self.right_operand)
        
        if self.left_isConstant:
            self.left_operand = int(self.left_operand)
        if self.right_isConstant:
            self.right_operand = int(self.right_operand)
    
    def _is_constant(self, value: int | str) -> bool:
        if isinstance(value, int):
            return True
        if isinstance(value, str):
            return value.isdigit() or (value.startswith('-') and value[1:].isdigit())
        return False
    
    def set_left_operand(self, new_left: int | str):
        self.left_operand = new_left
        self.left_isConstant = self._is_constant(new_left)
        if self.left_isConstant and isinstance(self.left_operand, str):
            self.left_operand = int(self.left_operand)
        self.update_line()
    
    def set_right_operand(self, new_right: int | str):
        self.right_operand = new_right
        self.right_isConstant = self._is_constant(new_right)
        if self.right_isConstant and isinstance(self.right_operand, str):
            self.right_operand = int(self.right_operand)
        self.update_line()

    def update_line(self):
        self.line = f"IF {self.left_operand} {self.operator} {self.right_operand} GOTO {self.target_label}"

class GotoHirLine(HirLine):
    def __init__(self, line:str):
        super().__init__(line)
        self.type = HirLineType.GOTO
        self.target_label = self.splitted[1]
    
    def set_target_label(self, new_target_label):
        self.target_label = new_target_label
        self.update_line()

    def update_line(self):
        self.line = f"GOTO {self.target_label}"

class LabelHirLine(HirLine):
    def __init__(self, line:str):
        super().__init__(line)
        self.type = HirLineType.LABEL
        self.label_name = self.splitted[0][:-1] 

class HirLineType:
    ASSIGNMENT = "ASSIGNMENT"
    ARITHMETIC_OP = "ARITHMETIC_OP"
    CONDITIONAL_OP = "CONDITIONAL_OP"
    UNARY_OP = "UNARY_OP"
    CALL_OP = "CALL_OP"
    IF_OP = "IF_OP"
    LABEL = "LABEL"
    GOTO = "GOTO"
