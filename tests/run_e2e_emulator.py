from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pycparser as pcp  # type: ignore[import-untyped]
from pycparser.c_ast import FileAST  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.AssemblyGen import AssemblyGenerator
from modules.HIRGen import generate_ir_high
from modules.HIROptimizer import optimize_hir
from modules.LIRGen import generate_ir_low
from modules.LIROptimizer import optimize_lir
from modules.SymbolTableGen import generate_symbol_table

SUPPORT_ROOT = Path(r"D:\Projects\ArniComp-Support-Package")
if str(SUPPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(SUPPORT_ROOT))
from emulator.cpu import CPU


@dataclass(frozen=True)
class Case:
    name: str
    filename: str
    expected: dict[str, int]


CASES: list[Case] = [
    Case(name="assign_const", filename="assign_const.c", expected={"a": 42}),
    Case(name="assign_copy", filename="assign_copy.c", expected={"a": 9, "b": 9}),
    Case(name="if_else_gt", filename="if_else_gt.c", expected={"a": 50, "b": 200}),
    Case(name="add_sub_chain", filename="add_sub_chain.c", expected={"a": 7, "b": 8, "c": 15}),
    Case(name="bitwise_combo", filename="bitwise_combo.c", expected={"c": 8, "d": 6, "e": 14}),
    Case(name="unary_ops", filename="unary_ops.c", expected={"bit": 254, "neg": 255, "not1": 0, "not0": 1}),
    Case(name="shift_left_const", filename="shift_left_const.c", expected={"b": 12, "c": 8}),
    Case(name="shift_left_var", filename="shift_left_var.c", expected={"out1": 12, "out2": 3}),
    Case(name="negative_and_wrap", filename="negative_and_wrap.c", expected={"a": 255, "b": 251, "c": 1, "d": 246}),
    Case(name="nested_if", filename="nested_if.c", expected={"out": 2}),
    Case(name="expr_temporaries", filename="expr_temporaries.c", expected={"out": 15}),
    Case(name="cond_compare_expr", filename="cond_compare_expr.c", expected={"gt": 1, "le": 0, "eq": 1, "ne": 1}),
    Case(name="cond_logic_expr", filename="cond_logic_expr.c", expected={"r1": 0, "r2": 1, "r3": 1, "r4": 0}),
    Case(name="call_inline_const", filename="call_inline_const.c", expected={"a": 8}),
]


def compile_case_to_assembly(c_path: Path) -> tuple[list[str], AssemblyGenerator]:
    parser = pcp.CParser(lex_optimize=True, yacc_optimize=True)
    code = c_path.read_text(encoding="utf-8")
    ast: FileAST = parser.parse(code, debug=False)

    symbol_table = generate_symbol_table(ast)
    hir_lines = generate_ir_high(ast)
    optimized_hir = optimize_hir(hir_lines, symbol_table)
    lir_lines = generate_ir_low(optimized_hir)
    optimized_lir = optimize_lir(lir_lines)

    asm_generator = AssemblyGenerator(symbol_table)
    asm_lines = asm_generator.generate_assembly_code(optimized_lir)
    return asm_lines, asm_generator


def write_asm_program(case_name: str, asm_lines: list[str], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    asm_path = output_dir / f"{case_name}.asm"
    final_lines = [line for line in asm_lines if line.strip() != ""]
    if not final_lines or final_lines[-1].strip().upper() != "HLT":
        final_lines.append("HLT")
    asm_path.write_text("\n".join(final_lines) + "\n", encoding="utf-8")
    return asm_path


def assemble_to_binary_text(asm_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    bin_txt_path = output_dir / f"{asm_path.stem}.machine.txt"
    assembler_dir = SUPPORT_ROOT / "assembler"

    helper_script = (
        "from modules.AssemblyHelper import AssemblyHelper\n"
        "from pathlib import Path\n"
        "import sys\n"
        "asm_path = Path(sys.argv[1])\n"
        "out_path = Path(sys.argv[2])\n"
        "helper = AssemblyHelper(comment_char=';', label_char=':', constant_keyword='equ', number_prefix='#', constant_prefix='$', label_prefix='@')\n"
        "raw_lines = asm_path.read_text(encoding='utf-8').splitlines(keepends=True)\n"
        "binary_lines, _, _ = helper.convert_to_machine_code(raw_lines)\n"
        "out_path.write_text(''.join(binary_lines), encoding='utf-8')\n"
    )
    command = [sys.executable, "-c", helper_script, str(asm_path), str(bin_txt_path)]
    result = subprocess.run(command, cwd=assembler_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Assembler failed for '{asm_path.name}'.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return bin_txt_path


def load_machine_text(bin_txt_path: Path) -> bytearray:
    program = bytearray()
    for line in bin_txt_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        program.append(int(stripped, 2))
    return program


def emulate(program: bytearray, max_cycles: int = 20000) -> CPU:
    cpu = CPU()
    cpu.load_program(program)

    cycles = 0
    while not cpu.halted and cycles < max_cycles:
        if not cpu.step():
            break
        cycles += 1

    if not cpu.halted:
        raise RuntimeError(f"Program did not halt within {max_cycles} cycles.")
    return cpu


def read_variable_value(cpu: CPU, asm_generator: AssemblyGenerator, variable_name: str) -> int:
    variable = asm_generator.variable_manager.get_variable(variable_name)
    if variable is None:
        raise ValueError(f"Variable '{variable_name}' not found in VariableManager.")
    address = variable.address.address
    return cpu.data_memory[address]


def run_case(case: Case, cases_dir: Path, artifacts_dir: Path) -> tuple[bool, str]:
    c_path = cases_dir / case.filename
    if not c_path.exists():
        return False, f"Case source not found: {c_path}"

    asm_lines, asm_generator = compile_case_to_assembly(c_path)
    asm_path = write_asm_program(case.name, asm_lines, artifacts_dir)
    machine_txt_path = assemble_to_binary_text(asm_path, artifacts_dir)
    program = load_machine_text(machine_txt_path)
    cpu = emulate(program)

    mismatches: list[str] = []
    for var_name, expected_value in case.expected.items():
        actual_value = read_variable_value(cpu, asm_generator, var_name)
        expected_u8 = expected_value & 0xFF
        if actual_value != expected_u8:
            mismatches.append(f"{var_name}: expected={expected_u8}, actual={actual_value}")

    if mismatches:
        return False, "; ".join(mismatches)
    return True, "PASS"


def main() -> int:
    if not SUPPORT_ROOT.exists():
        print(f"Support package path not found: {SUPPORT_ROOT}")
        return 2

    cases_dir = ROOT / "tests" / "e2e_cases"
    artifacts_dir = ROOT / "tests" / "e2e_artifacts"

    passed = 0
    failed = 0

    print("Running e2e compiler->assembler->emulator tests...")
    for case in CASES:
        try:
            ok, details = run_case(case, cases_dir, artifacts_dir)
        except Exception as exc:
            ok = False
            details = f"ERROR: {exc}"

        if ok:
            passed += 1
            print(f"[PASS] {case.name}")
        else:
            failed += 1
            print(f"[FAIL] {case.name} -> {details}")

    print(f"\nSummary: {passed} passed, {failed} failed, total {len(CASES)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
