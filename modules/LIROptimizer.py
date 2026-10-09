from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque

from entities.LirLine import (
    LirLine,
    SetMarLirLine,
    SetPrLirLine,
    LabelLirLine,
    GotoLirLine,
    ConditionalJumpLirLine,
)

class _UnsetMarState:
    pass


UNSET = _UnsetMarState()
MarState = str | None | _UnsetMarState


@dataclass
class BasicBlock:
    block_id: int
    start_idx: int
    end_idx: int
    predecessors: set[int] = field(default_factory=set)
    successors: set[int] = field(default_factory=set)
    in_mar: MarState = UNSET
    out_mar: MarState = UNSET


def _resolve_jump_targets(lir_lines: list[LirLine]) -> dict[int, str]:
    """
    Resolve jump target labels for GOTO/conditional jumps using SETPR flow.
    We conservatively reset PR tracking when a label is encountered.
    """
    jump_targets: dict[int, str] = {}
    current_pr_label: str | None = None

    for idx, lir in enumerate(lir_lines):
        if isinstance(lir, SetPrLirLine):
            current_pr_label = lir.target_label
        elif isinstance(lir, LabelLirLine):
            current_pr_label = None
        elif isinstance(lir, (GotoLirLine, ConditionalJumpLirLine)):
            if current_pr_label is not None:
                jump_targets[idx] = current_pr_label

    return jump_targets


def _build_basic_blocks(lir_lines: list[LirLine]) -> tuple[list[BasicBlock], dict[int, int]]:
    if not lir_lines:
        return [], {}

    label_to_index: dict[str, int] = {}
    for idx, lir in enumerate(lir_lines):
        if isinstance(lir, LabelLirLine):
            label_to_index[lir.label_name] = idx

    jump_targets = _resolve_jump_targets(lir_lines)

    leaders: set[int] = {0}
    for idx, lir in enumerate(lir_lines):
        if isinstance(lir, LabelLirLine):
            leaders.add(idx)

        if isinstance(lir, (GotoLirLine, ConditionalJumpLirLine)):
            if idx + 1 < len(lir_lines):
                leaders.add(idx + 1)

            target_label = jump_targets.get(idx)
            if target_label is not None and target_label in label_to_index:
                leaders.add(label_to_index[target_label])

    sorted_leaders = sorted(leaders)
    blocks: list[BasicBlock] = []
    index_to_block: dict[int, int] = {}

    for block_id, start_idx in enumerate(sorted_leaders):
        end_idx = sorted_leaders[block_id + 1] - 1 if block_id + 1 < len(sorted_leaders) else len(lir_lines) - 1
        block = BasicBlock(block_id=block_id, start_idx=start_idx, end_idx=end_idx)
        blocks.append(block)
        for i in range(start_idx, end_idx + 1):
            index_to_block[i] = block_id

    for block in blocks:
        last_idx = block.end_idx
        last_lir = lir_lines[last_idx]

        def add_successor(target_idx: int):
            if target_idx in index_to_block:
                succ_id = index_to_block[target_idx]
                block.successors.add(succ_id)
                blocks[succ_id].predecessors.add(block.block_id)

        if isinstance(last_lir, GotoLirLine):
            label = jump_targets.get(last_idx)
            if label is not None and label in label_to_index:
                add_successor(label_to_index[label])
        elif isinstance(last_lir, ConditionalJumpLirLine):
            label = jump_targets.get(last_idx)
            if label is not None and label in label_to_index:
                add_successor(label_to_index[label])
            if last_idx + 1 < len(lir_lines):
                add_successor(last_idx + 1)
        else:
            if last_idx + 1 < len(lir_lines):
                add_successor(last_idx + 1)

    return blocks, index_to_block


def _meet_mar_state(a: MarState, b: MarState) -> MarState:
    if isinstance(a, _UnsetMarState):
        return b
    if isinstance(b, _UnsetMarState):
        return a
    if a is None or b is None:
        return None
    return a if a == b else None


def _transfer_mar_state(block: BasicBlock, in_mar: str | None, lir_lines: list[LirLine]) -> str | None:
    mar_state: str | None = in_mar
    for idx in range(block.start_idx, block.end_idx + 1):
        lir = lir_lines[idx]
        if isinstance(lir, SetMarLirLine):
            mar_state = lir.destination_str
    return mar_state


def _analyze_block_mar_states(blocks: list[BasicBlock], lir_lines: list[LirLine]) -> None:
    if not blocks:
        return

    for block in blocks:
        block.in_mar = UNSET
        block.out_mar = UNSET

    # Entry block starts with unknown MAR content.
    blocks[0].in_mar = None
    work_queue = deque([0])

    while work_queue:
        block_id = work_queue.popleft()
        block = blocks[block_id]
        if isinstance(block.in_mar, _UnsetMarState):
            continue

        new_out = _transfer_mar_state(block, block.in_mar, lir_lines)
        if new_out != block.out_mar:
            block.out_mar = new_out

        for succ_id in block.successors:
            succ = blocks[succ_id]
            merged_in = _meet_mar_state(succ.in_mar, block.out_mar)
            if merged_in != succ.in_mar:
                succ.in_mar = merged_in
                work_queue.append(succ_id)

def remove_unnecessary_setmars(lir_lines:list[LirLine]) -> list[LirLine]:
    """
    CFG-aware SETMAR elimination.

    A SETMAR is removed only when MAR is guaranteed to already point to the same
    destination on all incoming paths to that program point.
    """
    blocks, _ = _build_basic_blocks(lir_lines)
    if not blocks:
        return lir_lines

    _analyze_block_mar_states(blocks, lir_lines)

    removable_indices: set[int] = set()
    for block in blocks:
        if isinstance(block.in_mar, _UnsetMarState):
            # Unreachable block from entry; keep as-is.
            continue

        current_mar: str | None = block.in_mar
        for idx in range(block.start_idx, block.end_idx + 1):
            lir = lir_lines[idx]
            if not isinstance(lir, SetMarLirLine):
                continue

            if current_mar == lir.destination_str:
                removable_indices.add(idx)
            else:
                current_mar = lir.destination_str

    return [lir for idx, lir in enumerate(lir_lines) if idx not in removable_indices]


def remove_unnecessary_setprs(lir_lines:list[LirLine]) -> list[LirLine]:
    """
    Remove redundant SETPR instructions when PR already points to the target label.
    Also invalidates PR tracking when a label is encountered (since we jumped here
    from somewhere else, PR state is unknown).
    """
    optimized_lir_lines = []
    current_pr_label = None

    for lir in lir_lines:
        if isinstance(lir, SetPrLirLine):
            if lir.target_label == current_pr_label:
                # PR already set to this label, skip
                continue
            else:
                current_pr_label = lir.target_label
        elif isinstance(lir, LabelLirLine):
            # When we reach a label, PR state becomes unknown
            # (we might have jumped here from anywhere)
            current_pr_label = None
        
        optimized_lir_lines.append(lir)

    return optimized_lir_lines


def optimize_lir(lir_lines:list[LirLine]) -> list[LirLine]:
    optimized_lir_lines = remove_unnecessary_setmars(lir_lines)
    optimized_lir_lines = remove_unnecessary_setprs(optimized_lir_lines)
    return optimized_lir_lines
