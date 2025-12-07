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
        self.source = self.splitted[1]
        self.destination = self.splitted[2]
    
    @staticmethod
    def create_line(destination:MovDestination, source:MovSource) -> MovLirLine:
        return MovLirLine(f"MOV {destination} {source}")
    

class MovDestinationType:
    VARIABLE = 'VARIABLE'
    REGISTER = 'REGISTER'

class MovSourceType:
    REGISTER = 'REGISTER'

class MovDestination:
    def __init__(self, type:MovDestinationType, value:str):
        if type is MovDestinationType.VARIABLE:
            self.value_str = f'var:{value}'
        elif type is MovDestinationType.REGISTER:
            self.value_str = value
        else:
            raise ValueError(f"Invalid MovDestinationType: {type}")
        
    def __str__(self):
        return self.value_str
    

class MovSource:
    def __init__(self, type:MovSourceType, value:str):
        if type is MovSourceType.REGISTER:
            if value not in SOURCE_REGISTERS_STR:
                raise ValueError(f"Invalid source register: {value}")
            self.value_str = value
        else:
            raise ValueError(f"Invalid MovSourceType: {type}")
    
    def __str__(self):
        return self.value_str
    

class LirLineType:
    LDI = 'LDI'
    MOV = 'MOV'

