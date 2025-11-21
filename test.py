from __future__ import annotations
import pycparser as pcp
from pycparser.c_ast import FileAST

from modules.FileHelper import read_file
from modules.SymbolTableGen import generate_symbol_table, SymbolTable
from modules.MemoryManager import VariableManager
from modules.IRGen import generate_ir_high, _op_eval

FILE_NAME = 'tests/define.c'
PARSER_DEBUG = False

def create_symbol_table():
    pass

def optimize_hir(hir_lines:list[str], symbol_table: SymbolTable) -> list[HirLine]:
    parsed_hir_lines = HirLine.parse_hir_lines(hir_lines)
    optimize_hir_lines = []
    static_vars = find_static_vars(parsed_hir_lines, symbol_table)
    optimized_hir_lines = paste_static_vars(parsed_hir_lines, static_vars)
    optimized_hir_lines = remove_unused_temporaries(optimized_hir_lines)
    print(static_vars)
    return optimized_hir_lines

def remove_unused_temporaries(hir_lines:list[HirLine]) -> list[HirLine]:
    optimized_hir_lines = []
    used_temps_count = get_temp_vars_used_count(hir_lines)
    for hir in hir_lines:
        if isinstance(hir, AssignmentHirLine):
            if hir.var_name.startswith('.t'):
                if used_temps_count.get(hir.var_name, 99) == 1:
                    continue
        elif isinstance(hir, ArithmeticOpHirLine):
            if hir.result_var.startswith('.t'):
                if used_temps_count.get(hir.result_var, 99) == 1:
                    continue
        elif isinstance(hir, ConditionalOpHirLine):
            if hir.result_var.startswith('.t'):
                if used_temps_count.get(hir.result_var, 99) == 1:
                    continue
        optimized_hir_lines.append(hir)
    return  optimized_hir_lines

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


def is_line_exists(hir_lines:list[HirLine], target_line:str) -> bool:
    for hir in hir_lines:
        if hir.line == target_line:
            return True
    return False

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

def generate_ir_low(hir_lines:list[HirLine]) -> list[str]:
    low_ir_lines = []
    for hir in hir_lines:
        print(hir.type)
    return low_ir_lines

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

class HirLine:
    def __init__(self, line:str):
        self.line = line
        self.splitted = line.split()
        self.splitted_len = len(self.splitted)
        self.type = None

    def __str__(self):
        return self.line
    

    @staticmethod
    def parse_hir_line(hir_line:str) -> HirLine:
        splitted = hir_line.split()
        splitted_len = len(splitted)
        if splitted_len == 3 and splitted[1] == '=':
            return AssignmentHirLine(hir_line)
        elif splitted_len == 5 and splitted[3] in ['+', '-', '*', '/', '%', '<<', '>>', '&', '|', '^']:
            return ArithmeticOpHirLine(hir_line)
        elif splitted_len == 5 and splitted[3] in ['==', '!=', '<', '<=', '>', '>=', '&&', '||']:
            return ConditionalOpHirLine(hir_line)
        elif splitted_len == 4 and splitted[0] == 'IF': 
            return IfOpHirLine(hir_line)
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
        self.value = self.splitted[2]
        self.isConstant = self.value.isdigit()
        if self.isConstant:
            self.value = int(self.value)

    def set_value(self, new_value):
        self.value = new_value
        self.update_line()

    def update_line(self):
        self.line = f"{self.var_name} = {self.value}"
    
class ArithmeticOpHirLine(HirLine):
    def __init__(self, line:str):
        super().__init__(line)
        self.type = HirLineType.ARITHMETIC_OP
        self.result_var = self.splitted[0]
        self.left_operand = self.splitted[2]
        self.operator = self.splitted[3]
        self.right_operand = self.splitted[4]
        self.left_isConstant = False
        self.right_isConstant = False
        self.set_left_operand(self.left_operand)
        self.set_right_operand(self.right_operand)
        if self.left_isConstant:
            self.left_operand = int(self.left_operand)
        if self.right_isConstant:
            self.right_operand = int(self.right_operand)
        
    def set_left_operand(self, new_left):
        self.left_operand = new_left
        if isinstance(self.left_operand, str):
            self.left_isConstant = self.left_operand.isdigit()
            self.left_operand = int(self.left_operand) if self.left_isConstant else self.left_operand
        elif isinstance(self.left_operand, int):
            self.left_isConstant = True
    
        self.evaluate_if_possible()
        self.update_line()

    def set_right_operand(self, new_right):
        self.right_operand = new_right
        if isinstance(self.right_operand, str):
            self.right_isConstant = self.right_operand.isdigit()
            self.right_operand = int(self.right_operand) if self.right_isConstant else self.right_operand
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
        self.left_operand = self.splitted[2]
        self.operator = self.splitted[3]
        self.right_operand = self.splitted[4]
        self.left_isConstant = self.left_operand.isdigit()
        self.right_isConstant = self.right_operand.isdigit()
        if self.left_isConstant:
            self.left_operand = int(self.left_operand)
        if self.right_isConstant:
            self.right_operand = int(self.right_operand)

    def set_left_operand(self, new_left):
        self.left_operand = new_left
        self.update_line()
        
    def set_right_operand(self, new_right):
        self.right_operand = new_right
        self.update_line()

    def update_line(self):
        self.line = f"{self.result_var} = {self.left_operand} {self.operator} {self.right_operand}"

class IfOpHirLine(HirLine):
    def __init__(self, line:str):
        super().__init__(line)
        self.type = HirLineType.IF_OP
        self.cond_var = self.splitted[1]
        self.target_label = self.splitted[3]
    
    def set_cond_var(self, new_cond_var):
        self.cond_var = new_cond_var
        self.update_line()

    def update_line(self):
        self.line = f"IF {self.cond_var} GOTO {self.target_label}"

class LabelHirLine(HirLine):
    def __init__(self, line:str):
        super().__init__(line)
        self.type = HirLineType.LABEL
        self.label_name = self.splitted[0][:-1] 

class HirLineType:
    ASSIGNMENT = "ASSIGNMENT"
    ARITHMETIC_OP = "ARITHMETIC_OP"
    CONDITIONAL_OP = "CONDITIONAL_OP"
    IF_OP = "IF_OP"
    LABEL = "LABEL"


def main():
    parser = pcp.CParser(lex_optimize=True, yacc_optimize=True)
    vm = VariableManager()
    code = read_file(FILE_NAME)
    print(code)
    ast:FileAST = parser.parse(code, debug=PARSER_DEBUG)

    symbol_table = generate_symbol_table(ast)
    vm.load_symbol_table(symbol_table)
    vm.print_variables()
    print(symbol_table.as_dict())
    hir_lines =  generate_ir_high(ast)
    print("---- HIR Lines ----")
    for line in hir_lines:
        print(line)


    optimized_hir_lines = optimize_hir(hir_lines, symbol_table)
    print("---- Optimized HIR Lines ----")
    
    for line in optimized_hir_lines:
        print(line)
    
    
    #lir_lines = generate_ir_low(optimized_hir_lines)


if __name__ == '__main__':
    main()