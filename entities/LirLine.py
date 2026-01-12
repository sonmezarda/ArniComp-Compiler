from __future__ import annotations

from helpers.ArchitectureHelper import SOURCE_REGISTERS_STR


class LirLine:
    def __init__(self, line:str):
        self.line = line
        self.splitted = line.split()
        self.splitted_len = len(self.splitted)
        self.type = None

    def __str__(self):
        return self.line    
    
    @staticmethod
    def parse_lir_line(lir_line:str) -> LirLine:
        return LirLine(lir_line)

class LoadImmLirLine(LirLine): 
    def __init__(self, line:str):
        super().__init__(line)
        if self.splitted[0] != LirLineType.LDI:
            raise ValueError(f"Invalid LIR line for LoadImmLirLine: {line}")
        self.type = LirLineType.LDI
        self.value:int = int(self.splitted[1])
    
    @staticmethod
    def create_line(value:int) -> LoadImmLirLine:
        return LoadImmLirLine(f"LDI {value}")

class MovLirLine(LirLine):
    def __init__(self, line:str):
        super().__init__(line)
        if self.splitted[0] != LirLineType.MOV:
            raise ValueError(f"Invalid LIR line for MovLirLine: {line}")
        self.type = LirLineType.MOV
        self.destination_str = self.splitted[1]
        self.source_str = self.splitted[2]

        self.source: MovSource = MovSource.parse(self.source_str)
        self.destination: MovDestination = MovDestination.parse(self.destination_str)
    
    @staticmethod
    def create_line(destination:MovDestination, source:MovSource) -> MovLirLine:
        return MovLirLine(f"MOV {destination} {source}")

class SetMarLirLine(LirLine):
    def __init__(self, line:str):
        super().__init__(line)
        if self.splitted[0] != 'SETMAR':
            raise ValueError(f"Invalid LIR line for SetMarLirLine: {line}")
        self.type = LirLineType.SETMAR
        self.destination_str = self.splitted[1]
        self.destination: MovDestination = MovDestination.parse(self.destination_str)
    
    @staticmethod
    def create_line(destination:MovDestination) -> SetMarLirLine:
        """
        Destination can be a variable or an address

        :param destination: Description
        :type destination: MovDestination
        :return: Returns a SetMarLirLine instance
        :rtype: SetMarLirLine
        """
        return SetMarLirLine(f"SETMAR {destination}")

class MovDestinationType:
    VARIABLE = 'VARIABLE'
    REGISTER = 'REGISTER'
    VARIABLE_ADDRESS = 'VARIABLE_ADDRESS'

class MovSourceType:
    REGISTER = 'REGISTER'
    VARIABLE = 'VARIABLE'

class MovDestination:
    def __init__(self, type:MovDestinationType, value:str):
        if type is MovDestinationType.VARIABLE:
            self.value_str = f'var:{value}'
            self.type = MovDestinationType.VARIABLE
            self.var = value
        elif type is MovDestinationType.REGISTER:
            self.value_str = value
            self.reg_name = value
            self.type = MovDestinationType.REGISTER
        elif type is MovDestinationType.VARIABLE_ADDRESS:
            self.value_str = f'var:{value}:addr'
            self.type = MovDestinationType.VARIABLE_ADDRESS
            self.var = value
        else:
            raise ValueError(f"Invalid MovDestinationType: {type}")
        
    def __str__(self):
        return self.value_str

    @staticmethod
    def parse(destination_str:str) -> MovDestination:
        if destination_str.startswith('var:') and destination_str.endswith(':addr'):
            var_name = destination_str[4:-5]
            return MovDestination(MovDestinationType.VARIABLE_ADDRESS, var_name)
        elif destination_str.startswith('var:'):
            var_name = destination_str[4:]
            return MovDestination(MovDestinationType.VARIABLE, var_name)
        else:
            return MovDestination(MovDestinationType.REGISTER, destination_str)    

class MovSource:
    def __init__(self, type:MovSourceType, value:str):
        if type is MovSourceType.REGISTER:
            if value not in SOURCE_REGISTERS_STR:
                raise ValueError(f"Invalid source register: {value}")
            self.value_str = value
            self.type = MovSourceType.REGISTER
            self.reg_name = value
        elif type is MovSourceType.VARIABLE:
            self.value_str = f'var:{value}'
            self.type = MovSourceType.VARIABLE
            self.var_name = value
        else:
            raise ValueError(f"Invalid MovSourceType: {type}")
    
    def __str__(self):
        return self.value_str

    def parse(source_str:str) -> MovSource:
        if source_str in SOURCE_REGISTERS_STR:
            return MovSource(MovSourceType.REGISTER, source_str)
        elif source_str.startswith('var:'):
            var_name = source_str[4:]
            return MovSource(MovSourceType.VARIABLE, var_name)
        else:
            raise ValueError(f"Invalid MovSource string: {source_str}")


class LirLineType:
    LDI = 'LDI'
    MOV = 'MOV'
    SETMAR = 'SETMAR'
    SETPR = 'SETPR'
    CMP = 'CMP'
    LABEL = 'LABEL'
    GOTO = 'GOTO'
    # Conditional jumps
    JEQ = 'JEQ'
    JNE = 'JNE'
    JLT = 'JLT'
    JLE = 'JLE'
    JGT = 'JGT'
    JGE = 'JGE'


class CmpLirLine(LirLine):
    """
    CMP source - Compare RD with source, sets flags (LT, GT, EQ)
    """
    def __init__(self, line: str):
        super().__init__(line)
        if self.splitted[0] != LirLineType.CMP:
            raise ValueError(f"Invalid LIR line for CmpLirLine: {line}")
        self.type = LirLineType.CMP
        self.source_str = self.splitted[1]
        self.source: MovSource = MovSource.parse(self.source_str)
    
    @staticmethod
    def create_line(source: MovSource) -> 'CmpLirLine':
        return CmpLirLine(f"CMP {source}")


class LabelLirLine(LirLine):
    """
    Label definition in LIR
    """
    def __init__(self, line: str):
        super().__init__(line)
        self.type = LirLineType.LABEL
        # Format: "label_name:"
        self.label_name = line.rstrip(':')
    
    @staticmethod
    def create_line(label_name: str) -> 'LabelLirLine':
        return LabelLirLine(f"{label_name}:")


class GotoLirLine(LirLine):
    """
    Unconditional jump in LIR (assumes PR is already set via SETPR)
    """
    def __init__(self, line: str):
        super().__init__(line)
        if self.splitted[0] != LirLineType.GOTO:
            raise ValueError(f"Invalid LIR line for GotoLirLine: {line}")
        self.type = LirLineType.GOTO
    
    @staticmethod
    def create_line() -> 'GotoLirLine':
        return GotoLirLine("GOTO")


class ConditionalJumpLirLine(LirLine):
    """
    Conditional jump in LIR (JEQ, JNE, JLT, JLE, JGT, JGE)
    Assumes PR is already set via SETPR
    """
    def __init__(self, line: str):
        super().__init__(line)
        self.jump_type = self.splitted[0]  # JEQ, JNE, JLT, etc.
        self.type = self.jump_type
    
    @staticmethod
    def create_line(jump_type: str) -> 'ConditionalJumpLirLine':
        return ConditionalJumpLirLine(f"{jump_type}")


class SetPrLirLine(LirLine):
    """
    Set Program Register (PR) to a label address.
    Similar to SETMAR but for jump targets.
    """
    def __init__(self, line: str):
        super().__init__(line)
        if self.splitted[0] != LirLineType.SETPR:
            raise ValueError(f"Invalid LIR line for SetPrLirLine: {line}")
        self.type = LirLineType.SETPR
        self.target_label = self.splitted[1]
    
    @staticmethod
    def create_line(target_label: str) -> 'SetPrLirLine':
        return SetPrLirLine(f"SETPR {target_label}")
