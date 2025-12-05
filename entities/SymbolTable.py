from __future__ import annotations

from enum import StrEnum

class SymbolKind(StrEnum):
    VARIABLE = 'variable'
    FUNCTION = 'function'

class SymbolType(StrEnum):
    INT = 'int'
    FLOAT = 'float'
    CHAR = 'char'
    VOID = 'void'

class SymbolScope(StrEnum):
    GLOBAL = 'global'
    LOCAL = 'local'

class SymbolQualifier(StrEnum):
    VOLATILE = 'volatile'
    CONST = 'const'

class Symbol:
    def __init__(self, name:str, kind:SymbolKind, type:SymbolType, scope:SymbolScope, qualifier:SymbolQualifier|None = None):
        self.name = name
        self.kind:SymbolKind = kind
        self.type:SymbolType = type
        self.scope:SymbolScope = scope
        self.qualifier:SymbolQualifier|None = qualifier
    
    def as_dict(self):
        dic = {
            'name': self.name,
            'type': self.type.value,
            'scope': self.scope.value,
            'kind': self.kind.value
        }
        if self.qualifier:
            dic['qualifier'] = self.qualifier.value
        return dic

class SymbolTable:
    def __init__(self):
        self.table: dict[str, Symbol] = {}
    
    def add(self, name:str, type:SymbolType, scope:SymbolScope, qualifier:SymbolQualifier|None = None):
        symbol = Symbol(name, type, scope, qualifier)
        self.table[name] = symbol

    def add_symbol(self, symbol:Symbol):
        self.table[symbol.name] = symbol

    def get(self, name:str) -> Symbol | None:
        return self.table.get(name, None)
    
    def is_exists(self, name:str) -> bool:
        return name in self.table
    
    def as_dict(self):
        return {name: symbol.as_dict() for name, symbol in self.table.items()}
