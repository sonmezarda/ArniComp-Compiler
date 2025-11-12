"""
IR Rules:

"""
import pycparser as pcp

def generate_ir(parsed_ast):
    # Placeholder for IR generation logic
    ir_representation = []
    # Traverse the AST and generate IR
    for ext in parsed_ast.ext:
        ir_representation.append(f"IR for {type(ext).__name__}")
    return ir_representation



if __name__ == '__main__':
    parser = pcp.CParser(lex_optimize=True, yacc_optimize=True)
    code = """
    int main() {
        return 0;
    }
    """
    ast = parser.parse(code)
    ir = generate_ir(ast)
    for line in ir:
        print(line)
