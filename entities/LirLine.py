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

class MovDestination:
    def __init__(self, type:MovDestinationType, value:str):
        if type is MovDestinationType.VARIABLE:
            self.value_str = f'var:{value}'
            self.type = MovDestinationType.VARIABLE
            self.var = value
        elif type is MovDestinationType.REGISTER:
            self.value_str = value
            self.register = value
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
        else:
            raise ValueError(f"Invalid MovSourceType: {type}")
    
    def __str__(self):
        return self.value_str

    def parse(source_str:str) -> MovSource:
        if source_str in SOURCE_REGISTERS_STR:
            return MovSource(MovSourceType.REGISTER, source_str)
        else:
            raise ValueError(f"Invalid MovSource string: {source_str}")


class LirLineType:
    LDI = 'LDI'
    MOV = 'MOV'
    SETMAR = 'SETMAR'
