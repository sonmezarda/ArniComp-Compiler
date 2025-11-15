from __future__ import annotations
from enum import StrEnum, Enum
from dataclasses import dataclass
from modules.SymbolTableGen import SymbolTable, SymbolScope, SymbolType, SymbolKind

@dataclass
class VariableType:
    name:str = ''
    size:int = 0
    is_signed:bool = False
    scope:str = '' # 'static', 'local', 'global'

class AddressType(StrEnum):
    STATIC = 'static'
    STACK = 'stack'

class VariableTypes:
    char = VariableType(name='char', size=1, is_signed=False)
    int = VariableType(name='int', size=2, is_signed=True)

class VariableAddress():
    def __init__(self, address:int, address_type:AddressType):
        self.address = address 
        self.address_type = address_type # 

class Variable:
    def __init__(self, name:str, type:VariableType, address:VariableAddress, scope:str = ''):
        self.name = name
        self.type = type
        self.address = address
        self.scope = scope
    
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
        
    def create_variable(self, name:str, type:VariableType, addrType:AddressType=AddressType.STATIC)-> Variable:
        if name in self.variables:
            raise ValueError(f"Variable '{name}' already exists.")
        if addrType == AddressType.STATIC:
            address = self.get_empty_address(type.size)
        else:
            raise NotImplementedError("Only STATIC address type is implemented.")
        var_address = VariableAddress(address, addrType)
        self.variables[name] = Variable(name, type, var_address)
        self.addresses[address] = self.variables[name]
        return self.variables[name] 
    
    def get_variable(self, name:str) -> Variable | None:
        return self.variables.get(name, None)
    
    def free_variable(self, name:str):
        var = self.variables.get(name, None)
        if var is None:
            raise ValueError(f"Variable '{name}' does not exist.")
        for offset in range(var.type.size):
            del self.addresses[var.address.address + offset]
        del self.variables[name]

    def print_variables(self):
        for var_name, var in self.variables.items():
            print(f"Variable '{var_name}': Type={var.type.name}, Address={var.address.address:#04x}")

    def load_symbol_table(self, symbol_table:SymbolTable):
        for symbol_name, symbol in symbol_table.table.items():
            if symbol.kind != SymbolKind.VARIABLE:
                continue
            if symbol.scope == SymbolScope.GLOBAL:
                if symbol.type == SymbolType.CHAR:
                    self.create_variable(symbol_name, VariableTypes.char, AddressType.STATIC)
                elif symbol.type == SymbolType.INT:
                    self.create_variable(symbol_name, VariableTypes.int, AddressType.STATIC)
                else:
                    raise NotImplementedError(f"Variable type '{symbol.type}' not implemented in VariableManager.")

if __name__ == '__main__':
    vm = VariableManager()
    vm.create_variable('var1', VariableTypes.char, AddressType.STATIC)
    vm.create_variable('var2', VariableTypes.char, AddressType.STATIC)
    vm.create_variable('var3', VariableTypes.int, AddressType.STATIC)
    vm.create_variable('var4', VariableTypes.int, AddressType.STATIC)
    for var_name, var in vm.variables.items():
        print(f"Variable '{var_name}': Type={var.type.name}, Address={var.address:#04x}")