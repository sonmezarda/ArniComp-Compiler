from entities.LirLine import *
from modules.MemoryManager import VariableManager, VariableTypes, AddressType, Variable
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

        self.assembly_lines: list[str] = []
        self.initialize_registers()

    def _get_or_create_variable(self, name: str) -> Variable:
        variable = self.variable_manager.get_variable(name)
        if variable is not None:
            return variable

        # Compiler temporaries (.tX) are spilled to memory in LIR lowering.
        if name.startswith('.t'):
            return self.variable_manager.create_variable(name, VariableTypes.char, AddressType.STATIC)

        raise ValueError(f"Variable '{name}' not found in VariableManager.")

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
                    if movDestination.var is None or movSource.reg_name is None:
                        raise ValueError("Invalid MOV operands for variable store.")
                    variable = self._get_or_create_variable(movDestination.var)
                    
                    if self._is_mar_cache_known():
                        is_var_addr_set = self.register_manager.check_mar_address(variable.address.address)
                        if not is_var_addr_set:
                            raise ValueError(f"MAR does not point to the address of variable {movDestination.var}\n Var addr: {variable.address.address:#04x} \n MAR addr: {self.register_manager.get_mar_address():#04x}")
                    
                    source_reg = movSource.reg_name
                    assembly_lines.append(ASM_instructions.STORE(source_reg))
                elif movDestination.type == MovDestinationType.REGISTER and movSource.type == MovSourceType.VARIABLE:
                    if movSource.var_name is None or movDestination.reg_name is None:
                        raise ValueError("Invalid MOV operands for variable load.")
                    variable = self._get_or_create_variable(movSource.var_name)
                    
                    if self._is_mar_cache_known():
                        is_var_addr_set = self.register_manager.check_mar_address(variable.address.address)
                        if not is_var_addr_set:
                            raise ValueError(f"MAR does not point to the address of variable {movSource.var_name}\n Var addr: {variable.address.address:#04x} \n MAR addr: {self.register_manager.get_mar_address():#04x}")
                    
                    dest_reg = movDestination.reg_name
                    assembly_lines.append(ASM_instructions.LOAD(dest_reg))
                elif movDestination.type == MovDestinationType.REGISTER and movSource.type == MovSourceType.REGISTER:
                    if movDestination.reg_name is None or movSource.reg_name is None:
                        raise ValueError("Invalid MOV operands for register-to-register move.")
                    dest_reg_name = movDestination.reg_name
                    src_reg_name = movSource.reg_name
                    if dest_reg_name != src_reg_name:
                        assembly_lines.append(ASM_instructions.MOV(dest_reg_name, src_reg_name))

                    src_reg = self.register_manager.get_register(src_reg_name)
                    if src_reg is not None and src_reg.content is not None:
                        self.register_manager.allocate_register(dest_reg_name, src_reg.content)
                    else:
                        self.register_manager.free_register(dest_reg_name)
                else:
                    raise ValueError("Unsupported MOV combination in AssemblyGenerator.")
            elif isinstance(lir, SetMarLirLine):
                mar_destination = lir.destination
                if mar_destination.type == MovDestinationType.VARIABLE_ADDRESS:
                    if mar_destination.var is None:
                        raise ValueError("SETMAR variable destination is missing variable name.")
                    variable = self._get_or_create_variable(mar_destination.var)
                    
                    assembly_lines.extend(self._ASM_set_mar_constant(variable.address.address))

                else:
                    raise ValueError("SETMAR destination must be of type VARIABLE_ADDRESS.")
            
            elif isinstance(lir, CmpLirLine):
                # CMP source - compare RD with source
                source = lir.source
                if source.type == MovSourceType.REGISTER:
                    if source.reg_name is None:
                        raise ValueError("CMP register source is missing register name.")
                    assembly_lines.append(ASM_instructions.CMP(source.reg_name))
                elif source.type == MovSourceType.VARIABLE:
                    # CMP M (memory at MAR)
                    assembly_lines.append(ASM_instructions.CMP('M'))
                else:
                    raise ValueError(f"Unsupported CMP source type: {source.type}")

            elif isinstance(lir, AluOpLirLine):
                source = lir.source
                if source.type == MovSourceType.REGISTER:
                    if source.reg_name is None:
                        raise ValueError("ALU register source is missing register name.")
                    assembly_lines.append(ASM_instructions.ALU(lir.opcode, source.reg_name))
                elif source.type == MovSourceType.VARIABLE:
                    assembly_lines.append(ASM_instructions.ALU(lir.opcode, 'M'))
                else:
                    raise ValueError(f"Unsupported ALU source type: {source.type}")
            
            elif isinstance(lir, LabelLirLine):
                # Label definition
                # Control-flow joins invalidate linear register cache assumptions.
                self._invalidate_control_flow_cache()
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

        assembly_lines = self._resolve_setpr_placeholders(assembly_lines)
        assembly_lines = [line for line in assembly_lines if line.strip() != ""]
        return assembly_lines
    
    def _ASM_load_imm_constant(self, value:int) -> str:
        ra = self.register_manager.get_register('RA')
        if (
            ra is not None
            and ra.content is not None
            and ra.content.content_type == RegisterContentType.CONSTANT
            and ra.content.value == value
        ):
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

        if (
            dest_reg.content is not None
            and src_reg.content is not None
            and dest_reg.content.content_type == src_reg.content.content_type
            and dest_reg.content.content_type == RegisterContentType.CONSTANT
            and dest_reg.content.value == src_reg.content.value
        ):
                return ""  # No need to move if both registers have the same constant value

        if src_reg.content is not None:
            self.register_manager.allocate_register(dest_reg_name, src_reg.content)
        else:
            self.register_manager.free_register(dest_reg_name)
        return ASM_instructions.MOV(dest_reg_name, src_reg_name)
    
    def _ASM_set_mar_constant(self, address:int) -> list[str]:
        mar_low = address & 0x00FF
        mar_high = (address >> 8) & 0x00FF
        
        marl = self.register_manager.get_register('MARL')
        marh = self.register_manager.get_register('MARH')

        if marl is None or marh is None:
            raise ValueError("MAR registers not found.")
        
        lines:list[str] = []
        marl_is_known = (
            marl.content is not None
            and marl.content.content_type == RegisterContentType.CONSTANT
            and marl.content.value == mar_low
        )
        if not marl_is_known:
            lines.append(ASM_instructions.LDI(mar_low))
            self.register_manager.allocate_register('RA', RegisterContent(RegisterContentType.CONSTANT, value=mar_low))
            lines.append(ASM_instructions.MOV('MARL', 'RA'))
            self.register_manager.allocate_register('MARL', RegisterContent(RegisterContentType.CONSTANT, value=mar_low))
        marh_is_known = (
            marh.content is not None
            and marh.content.content_type == RegisterContentType.CONSTANT
            and marh.content.value == mar_high
        )
        if not marh_is_known:
            lines.append(ASM_instructions.LDI(mar_high))
            self.register_manager.allocate_register('RA', RegisterContent(RegisterContentType.CONSTANT, value=mar_high))
            lines.append(ASM_instructions.MOV('MARH', 'RA'))
            self.register_manager.allocate_register('MARH', RegisterContent(RegisterContentType.CONSTANT, value=mar_high))
        
        return lines

    def _invalidate_mar_cache(self) -> None:
        self.register_manager.free_register('MARL')
        self.register_manager.free_register('MARH')

    def _is_mar_cache_known(self) -> bool:
        marl = self.register_manager.get_register('MARL')
        marh = self.register_manager.get_register('MARH')
        return (
            marl is not None
            and marh is not None
            and marl.content is not None
            and marh.content is not None
            and marl.content.content_type == RegisterContentType.CONSTANT
            and marh.content.content_type == RegisterContentType.CONSTANT
            and isinstance(marl.content.value, int)
            and isinstance(marh.content.value, int)
        )

    def _invalidate_control_flow_cache(self) -> None:
        # Any control-flow join can arrive with different register states.
        for reg_name in ['RA', 'RB', 'RD', 'ACC', 'PRL', 'PRH', 'PCL', 'PCH', 'MARL', 'MARH']:
            self.register_manager.free_register(reg_name)
    
    def _ASM_set_pr(self, target_label: str) -> list[str]:
        """
        Emit deferred SETPR placeholder.
        Real encoding is done in _resolve_setpr_placeholders using resolved label addresses.
        """
        return [ASM_instructions.SETPR_PLACEHOLDER(target_label)]

    def _resolve_setpr_placeholders(self, assembly_lines: list[str]) -> list[str]:
        """
        Resolve __SETPR__ placeholders in two passes.

        Pass-1 computes instruction addresses with fixed placeholder size:
          __SETPR__ <label> -> 3 instructions:
            LDI low7
            SMSBRA or NOP
            MOV PRL, RA
        """
        label_to_address: dict[str, int] = {}
        pc = 0
        for line in assembly_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(';'):
                continue
            if stripped.endswith(':'):
                label_to_address[stripped[:-1]] = pc
                continue
            if stripped.startswith("__SETPR__ "):
                pc += 3
                continue
            pc += 1

        resolved: list[str] = []
        for line in assembly_lines:
            stripped = line.strip()
            if stripped.startswith("__SETPR__ "):
                target_label = stripped.split(maxsplit=1)[1]
                if target_label not in label_to_address:
                    raise ValueError(f"Unknown label in SETPR: '{target_label}'")

                target_addr = label_to_address[target_label] & 0xFF
                resolved.append(ASM_instructions.LDI(target_addr & 0x7F))
                if target_addr & 0x80:
                    resolved.append(ASM_instructions.SETMSBRA())
                else:
                    resolved.append(ASM_instructions.NOP())
                resolved.append(ASM_instructions.MOV('PRL', 'RA'))

                self.register_manager.allocate_register('RA', RegisterContent(RegisterContentType.CONSTANT, value=target_addr))
                self.register_manager.allocate_register('PRL', RegisterContent(RegisterContentType.CONSTANT, value=target_addr))
                continue
            resolved.append(line)
        return resolved
    
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
    def ALU(opcode:str, source:str) -> str:
        return f"{opcode} {source}"
    
    @staticmethod
    def LABEL(label_name:str) -> str:
        return f"{label_name}:"
    
    @staticmethod
    def JMP() -> str:
        return "JMP"

    @staticmethod
    def NOP() -> str:
        return "NOP"
    
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

    @staticmethod
    def SETPR_PLACEHOLDER(label_name: str) -> str:
        return f"__SETPR__ {label_name}"
