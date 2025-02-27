# Copyright (c) 2023 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import dataclasses

from paddle.jit.utils import OrderedSet

from .instruction_utils import Instruction
from .opcode_info import (
    ALL_JUMP,
    HAS_FREE,
    HAS_LOCAL,
    RETURN,
    UNCONDITIONAL_JUMP,
)


@dataclasses.dataclass
class State:
    reads: OrderedSet[str]
    writes: OrderedSet[str]
    visited: OrderedSet[int]

    def __or__(self, other):
        reads = self.reads | other.reads
        writes = self.writes | other.writes
        return State(reads, writes, OrderedSet())


def is_read_opcode(opname):
    if opname in [
        "LOAD_FAST",
        "LOAD_DEREF",
        "LOAD_NAME",
        "LOAD_GLOBAL",
        "LOAD_CLOSURE",
    ]:
        return True
    if opname in (
        "DELETE_FAST",
        "DELETE_DEREF",
        "DELETE_NAME",
        "DELETE_GLOBAL",
    ):
        return True
    return False


def is_write_opcode(opname):
    if opname in ["STORE_FAST", "STORE_NAME", "STORE_DEREF", "STORE_GLOBAL"]:
        return True
    if opname in (
        "DELETE_FAST",
        "DELETE_DEREF",
        "DELETE_NAME",
        "DELETE_GLOBAL",
    ):
        return True
    return False


def analysis_used_names(
    instructions: list[Instruction],
    current_instr_idx: int,
    stop_instr_idx: int | None = None,
) -> OrderedSet[str]:
    """
    Analyze the inputs of the instructions from current_instr_idx to stop_instr_idx.

    Args:
        instructions (list[Instruction]): The instructions to analyze.
        current_instr_idx (int): The index of the current instruction.
        stop_instr_idx (int | None, optional): The index of the instruction to stop. Defaults to None.
            If None, the analysis will stop at the end of the instructions.

    Returns:
        set[str]: The analysis result.
    """
    root_state = State(OrderedSet(), OrderedSet(), OrderedSet())

    def fork(
        state: State, start: int, jump: bool, jump_target: int
    ) -> OrderedSet[str]:
        new_start = start + 1 if not jump else jump_target
        new_state = State(
            OrderedSet(state.reads),
            OrderedSet(state.writes),
            OrderedSet(state.visited),
        )
        return walk(new_state, new_start)

    def walk(state: State, start: int) -> OrderedSet[str]:
        end = len(instructions) if stop_instr_idx is None else stop_instr_idx
        for i in range(start, end):
            if i in state.visited:
                return state
            state.visited.add(i)

            instr = instructions[i]
            if instr.opname in HAS_LOCAL | HAS_FREE:
                if is_read_opcode(instr.opname) and instr.argval not in (
                    state.writes
                ):
                    state.reads.add(instr.argval)
                elif is_write_opcode(instr.opname):
                    state.writes.add(instr.argval)
            elif instr.opname in ALL_JUMP:
                assert instr.jump_to is not None
                target_idx = instructions.index(instr.jump_to)
                # Fork to two branches, jump or not
                jump_branch = fork(state, i, True, target_idx)
                not_jump_branch = (
                    fork(state, i, False, target_idx)
                    if instr.opname not in UNCONDITIONAL_JUMP
                    else State(OrderedSet(), OrderedSet(), OrderedSet())
                )
                return jump_branch | not_jump_branch
            elif instr.opname in RETURN:
                return state
        return state

    state = walk(root_state, current_instr_idx)
    return state.reads, state.writes
