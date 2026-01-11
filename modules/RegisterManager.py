from enum import StrEnum
from modules.Config import REGISTER_MAX_VALUE, REGISTERS

class RegisterContentType(StrEnum):
    EMPTY = 'empty'
    VARIABLE = 'variable'
    CONSTANT = 'constant'
    VARIABLE_ADDRESS = 'variable_address'

class RegisterContent:
    def __init__(self, content_type:RegisterContentType, value:int|None = None, variable_name:str|None = None):
        if content_type == RegisterContentType.EMPTY:
            self.content_type = RegisterContentType.EMPTY
            value = None
        elif content_type == RegisterContentType.CONSTANT:
            if value is None:
                raise ValueError("Constant register content must have a value.")
            if value > REGISTER_MAX_VALUE:
                raise ValueError(f"Constant value {value} exceeds max register value {REGISTER_MAX_VALUE}.")
            if variable_name is not None:
                raise ValueError("Constant register content should not have a variable name.")

            self.content_type = RegisterContentType.CONSTANT
            self.value = value
            self.variable_name = None
        elif content_type == RegisterContentType.VARIABLE:
            if value is not None:
                raise ValueError("Variable register content should not have a direct value.")
            if not variable_name:
                raise ValueError("Variable register content must have a variable name.")
            self.content_type = RegisterContentType.VARIABLE
            self.variable_name = variable_name
            self.value = None
        elif content_type == RegisterContentType.VARIABLE_ADDRESS:
            if value is not None:
                raise ValueError("Variable address register content should not have a direct value.")
            if not variable_name:
                raise ValueError("Variable address register content must have a variable name.")
            self.content_type = RegisterContentType.VARIABLE_ADDRESS
            self.variable_name = variable_name
            self.value = None
        else:
            raise ValueError("Invalid register content type.")


class Register():
    def __init__(self, name:str, readable:bool = True, writable:bool = True):
        self.name = name
        self.readable = readable
        self.writable = writable
        self.is_allocated = False
        self.content = None
    
    def allocate(self, content:RegisterContent):
        self.is_allocated = True
        self.content = content
    
    def free(self):
        self.is_allocated = False
        self.content = None
    

class RegisterManager:
    def __init__(self, register_config:dict[int, dict[str, any]]):
        self.registers: dict[str, Register] = {}
        for reg_info in register_config.values():
            reg = Register(name=reg_info['NAME'], readable=reg_info['READABLE'], writable=reg_info['WRITABLE'])
            self.registers[reg.name] = reg
    
    def get_register(self, name:str) -> Register:
        return self.registers.get(name, None)
    
    def free_register(self, name:str):
        reg = self.get_register(name)
        if reg:
            reg.free()
    
    def allocate_register(self, name:str, content:RegisterContent) -> Register:
        reg = self.get_register(name)
        if reg:
            reg.allocate(content)
            return reg
        return None
    
    def get_free_register(self) -> Register | None:
        for reg in self.registers.values():
            if not reg.is_allocated:
                return reg
        return None
    
class ArnicompRegisterManager(RegisterManager):
    def __init__(self):
        super().__init__(REGISTERS)
    
    def get_mar_registers(self) -> tuple[Register, Register]:
        marl_low = self.get_register('MARL')
        marl_high = self.get_register('MARH')
        return (marl_low, marl_high)

    def get_mar_address(self) -> int:
        marl_low = self.get_register('MARL')
        marl_high = self.get_register('MARH')
        if marl_low.content is None or marl_high.content is None:
            raise ValueError("MAR registers are not properly set.")
        address = (marl_high.content.value << 8) | marl_low.content.value
        return address

    def check_mar_address(self, address:int) -> bool:
        return address == self.get_mar_address()