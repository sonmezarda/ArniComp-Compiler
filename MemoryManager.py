from __future__ import annotations
from enum import StrEnum, Enum
from dataclasses import dataclass

@dataclass
class VariableType:
    name:str = ''
    size:int = 0
    is_signed:bool = False


class VariableTypes:
    char = VariableType(name='char', size=1, is_signed=False)
    int = VariableType(name='int', size=2, is_signed=True)

class Variable:
    def __init__(self, name:str, type:VariableType, address:int):
        self.name = name
        self.type = type
        self.address = address

class VariableManager:
    def __init__(self, static_start_address:int=0, static_end_address:int=0x00FF):
        self.static_start_address = static_start_address
        self.static_end_address = static_end_address
        self.variables: dict[str, Variable] = {}
        self.addresses: dict[int, Variable] = {}
    
    def get_empty_address(self, size:int) -> int:
        for addr in range(self.static_start_address, self.static_end_address - size + 1):
            if all((addr + offset) not in self.addresses for offset in range(size)):
                for offset in range(size):
                    self.addresses[addr + offset] = None
                return addr
        raise MemoryError("No empty addresses available.")
        
    def create_variable(self, name:str, type:VariableType)-> Variable:
        if name in self.variables:
            raise ValueError(f"Variable '{name}' already exists.")
        address = self.get_empty_address(type.size)
        self.variables[name] = Variable(name, type, address)
        self.addresses[address] = self.variables[name]
        return self.variables[name] 
    
    def get_variable(self, name:str) -> Variable | None:
        return self.variables.get(name, None)

if __name__ == '__main__':
    vm = VariableManager()
    vm.create_variable('var1', VariableTypes.char)
    vm.create_variable('var2', VariableTypes.char)
    vm.create_variable('var3', VariableTypes.int)
    vm.create_variable('var4', VariableTypes.int)
    for var_name, var in vm.variables.items():
        print(f"Variable '{var_name}': Type={var.type.name}, Address={var.address:#04x}")