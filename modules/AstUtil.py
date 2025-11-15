from pycparser.c_ast import FileAST,FuncDef

def get_main_function(ast:FileAST) -> FuncDef | None:
    for ext in ast.ext:
        if isinstance(ext, FuncDef):
            if ext.decl.name == 'main':
                return ext
    return None