from entities.LirLine import *
from modules.MemoryManager import VariableManager
from modules.SymbolTableGen import SymbolTable
from modules.RegisterManager import RegisterManager, Register, RegisterContent, RegisterContentType, ArnicompRegisterManager
from helpers.ArchitectureHelper import MAX_LDI_VALUE
class AssemblyGenerator:
    def __init__(self, symbolTable: SymbolTable):
        self.symbol_table = symbolTable
        vm = VariableManager()   
        vm.load_symbol_table(symbolTable)
        self.variable_manager = vm
        self.register_manager = ArnicompRegisterManager()

        self.assembly_lines = []
        self.initialize_registers()

    def initialize_registers(self) -> list[str]:
        init_reg_Lines:list[str] = [
            ASM_instructions.LDI(0),
            ASM_instructions.MOV('MARL', 'RA'),
            ASM_instructions.MOV('MARH', 'RA')
        ]
        self.register_manager.allocate_register('RA', RegisterContent(RegisterContentType.CONSTANT, value=0))
        self.register_manager.allocate_register('MARL', RegisterContent(RegisterContentType.CONSTANT, value=0))
        self.register_manager.allocate_register('MARH', RegisterContent(RegisterContentType.CONSTANT, value=0))
        
        self.assembly_lines.extend(init_reg_Lines)
        self.assembly_lines.append(ASM_instructions.COMMENT("---- End of Initialization ----"))
        return init_reg_Lines

    def generate_assembly_code(self, lir_lines:list[LirLine]) -> list[str]:
        assembly_lines:list[str] = self.assembly_lines
        for lir in lir_lines:
            if isinstance(lir, LoadImmLirLine):
                if lir.value > MAX_LDI_VALUE:
                    value_to_set = lir.value & 0b01111111
                    assembly_lines.append(ASM_instructions.LDI(value_to_set))
                    assembly_lines.append(ASM_instructions.SETMSBRA())
                else:
                    assembly_lines.append(self._ASM_load_imm_constant(lir.value))
            elif isinstance(lir, MovLirLine):
                movDestination = lir.destination
                movSource = lir.source
                if movDestination.type == MovDestinationType.VARIABLE and movSource.type == MovSourceType.REGISTER:
                    variable = self.variable_manager.get_variable(movDestination.var)
                    if variable is None:
                        raise ValueError(f"Variable '{movDestination.var}' not found in VariableManager.")
                    
                    is_var_addr_set = self.register_manager.check_mar_address(variable.address.address)
                    if not is_var_addr_set:
                        raise ValueError(f"MAR does not point to the address of variable {movDestination.var}\n Var addr: {variable.address.address:#04x} \n MAR addr: {self.register_manager.get_mar_address():#04x}")
                    
                    source_reg = movSource.reg_name
                    assembly_lines.append(ASM_instructions.STORE(source_reg))
                elif movDestination.type == MovDestinationType.REGISTER and movSource.type == MovSourceType.VARIABLE:
                    variable = self.variable_manager.get_variable(movSource.var_name)
                    if variable is None:
                        raise ValueError(f"Variable '{movSource.var_name}' not found in VariableManager.")
                    
                    is_var_addr_set = self.register_manager.check_mar_address(variable.address.address)
                    if not is_var_addr_set:
                        raise ValueError(f"MAR does not point to the address of variable {movSource.var_name}\n Var addr: {variable.address.address:#04x} \n MAR addr: {self.register_manager.get_mar_address():#04x}")
                    
                    dest_reg = movDestination.reg_name
                    assembly_lines.append(ASM_instructions.LOAD(dest_reg))
                else:
                    raise ValueError("Only MOV from REGISTER to VARIABLE is implemented in this Assembly generator.")
            elif isinstance(lir, SetMarLirLine):
                mar_destination = lir.destination
                if mar_destination.type == MovDestinationType.VARIABLE_ADDRESS:
                    variable = self.variable_manager.get_variable(mar_destination.var)
                    if variable is None:
                        raise ValueError(f"Variable '{mar_destination.var}' not found in VariableManager.")
                    
                    assembly_lines.extend(self._ASM_set_mar_constant(variable.address.address))

                else:
                    raise ValueError("SETMAR destination must be of type VARIABLE_ADDRESS.")
            
            elif isinstance(lir, CmpLirLine):
                # CMP source - compare RD with source
                source = lir.source
                if source.type == MovSourceType.REGISTER:
                    assembly_lines.append(ASM_instructions.CMP(source.reg_name))
                elif source.type == MovSourceType.VARIABLE:
                    # CMP M (memory at MAR)
                    assembly_lines.append(ASM_instructions.CMP('M'))
                else:
                    raise ValueError(f"Unsupported CMP source type: {source.type}")
            
            elif isinstance(lir, LabelLirLine):
                # Label definition
                assembly_lines.append(ASM_instructions.LABEL(lir.label_name))
            
            elif isinstance(lir, SetPrLirLine):
                # Set Program Register to label address
                assembly_lines.extend(self._ASM_set_pr(lir.target_label))
            
            elif isinstance(lir, GotoLirLine):
                # Unconditional jump (PR already set via SETPR)
                assembly_lines.append(ASM_instructions.JMP())
            
            elif isinstance(lir, ConditionalJumpLirLine):
                # Conditional jump (PR already set via SETPR)
                assembly_lines.append(ASM_instructions.CONDITIONAL_JUMP(lir.jump_type))
            
            else:
                print("Unhandled LIR line type:", type(lir))
        
        assembly_lines = [line for line in assembly_lines if line.strip() != ""]
        return assembly_lines
    
    def _ASM_load_imm_constant(self, value:int) -> str:
        ra = self.register_manager.get_register('RA')
        if ra.content.content_type == RegisterContentType.CONSTANT and ra.content.value == value:
            return ""  # No need to load if RA already has the constant value
        
        self.register_manager.allocate_register('RA', RegisterContent(RegisterContentType.CONSTANT, value=value))
        return ASM_instructions.LDI(value)
    

    def _ASM_mov(self, dest_reg_name:str, src_reg_name:str) -> str:
        if dest_reg_name == src_reg_name:
            return ""  # No need to move if source and destination are the same
        
        dest_reg = self.register_manager.get_register(dest_reg_name)
        src_reg = self.register_manager.get_register(src_reg_name)

        if dest_reg is None or src_reg is None:
            raise ValueError(f"Invalid register names: dest='{dest_reg_name}', src='{src_reg_name}'")
        
        if dest_reg.content.content_type == src_reg.content.content_type:
            if dest_reg.content.content_type == RegisterContentType.CONSTANT and dest_reg.content.value == src_reg.content.value:
                return ""  # No need to move if both registers have the same constant value
        
        self.register_manager.allocate_register(dest_reg_name, src_reg.content)
        return ASM_instructions.MOV(dest_reg_name, src_reg_name)
    
    def _ASM_set_mar_constant(self, address:int) -> list[str]:
        mar_low = address & 0x00FF
        mar_high = (address >> 8) & 0x00FF
        
        marl = self.register_manager.get_register('MARL')
        marh = self.register_manager.get_register('MARH')

        if marl is None or marh is None:
            raise ValueError("MAR registers not found.")
        
        lines:list[str] = []
        if marl.content.content_type != RegisterContentType.CONSTANT or marl.content.value != mar_low:
            lines.append(ASM_instructions.LDI(mar_low))
            self.register_manager.allocate_register('RA', RegisterContent(RegisterContentType.CONSTANT, value=mar_low))
            lines.append(ASM_instructions.MOV('MARL', 'RA'))
            self.register_manager.allocate_register('MARL', RegisterContent(RegisterContentType.CONSTANT, value=mar_low))
        if marh.content.content_type != RegisterContentType.CONSTANT or marh.content.value != mar_high:
            lines.append(ASM_instructions.LDI(mar_high))
            self.register_manager.allocate_register('RA', RegisterContent(RegisterContentType.CONSTANT, value=mar_high))
            lines.append(ASM_instructions.MOV('MARH', 'RA'))
            self.register_manager.allocate_register('MARH', RegisterContent(RegisterContentType.CONSTANT, value=mar_high))
        
        return lines
    
    def _ASM_set_pr(self, target_label: str) -> list[str]:
        """
        Set Program Register (PRL) to label address.
        Note: For 8-bit architecture, we only use PRL for now.
        PRH support can be added for larger address space.
        """
        lines: list[str] = []
        # TODO: Add optimization to skip if PRL already has this label
        lines.append(ASM_instructions.LDI_LABEL(target_label))
        self.register_manager.allocate_register('RA', RegisterContent(RegisterContentType.LABEL, value=target_label))
        lines.append(ASM_instructions.MOV('PRL', 'RA'))
        return lines
    
class ASM_instructions:
    @staticmethod
    def LDI(value:int) -> str:
        return f"LDI {value}"
    
    @staticmethod
    def MOV(destination:str, source:str) -> str:
        return f"MOV {destination}, {source}"
    
    @staticmethod
    def COMMENT(comment:str) -> str:
        return f"; {comment}"
    
    @staticmethod
    def STORE(reg_name:str) -> str:
        return f"MOV M, {reg_name}"

    @staticmethod
    def LOAD(reg_name:str) -> str:
        return f"MOV {reg_name}, M"
    
    @staticmethod
    def CMP(source:str) -> str:
        return f"CMP {source}"
    
    @staticmethod
    def LABEL(label_name:str) -> str:
        return f"{label_name}:"
    
    @staticmethod
    def JMP() -> str:
        return "JMP"
    
    @staticmethod
    def CONDITIONAL_JUMP(jump_type:str) -> str:
        """Generate conditional jump instruction (JEQ, JNE, JLT, JLE, JGT, JGE)"""
        return jump_type
    
    @staticmethod
    def SETMSBRA() -> str:
        """Set most significant bit of RA = 1
        Ra = [1:Ra[7:0]]
        """
        return "SMSBRA"


    @staticmethod
    def LDI_LABEL(label_name:str) -> str:
        """Load label address into RA using @ prefix"""
        return f"LDI @{label_name}"