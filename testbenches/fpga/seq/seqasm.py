# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Assemble the master board's programs into its sequencer ROM.

    python3 testbenches/fpga/seq/seqasm.py testbenches/fpga/seq/programs.seq -o build/seq.mem
    python3 testbenches/fpga/seq/seqasm.py --self-test

A ROM word is op[31:28], addr[20:16], data[15:0], decoded by seq_core.sv.
Words 0 to 15 are the start address of the program on each DIP switch
setting, word 16 is a HALT that every unused setting points at.

Every TEST_CTRL_0 write is checked against regmap.py, so a program that could
short the bias nodes on silicon does not assemble.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "models"))
import regmap  # noqa: E402

OP_HALT, OP_SPI, OP_WAITC, OP_STREAM, OP_CAPT, OP_LOOP, OP_RESET = range(7)
ROM_DEPTH = 256
N_PROGRAMS = 16
HALT_PC = 16


class AsmError(Exception):
    pass


def word(op: int, addr: int = 0, data: int = 0) -> int:
    return (op << 28) | ((addr & 0x1F) << 16) | (data & 0xFFFF)


def _int(tok: str, where: str, hi: int) -> int:
    try:
        v = int(tok, 0)
    except ValueError:
        raise AsmError(f"{where}: '{tok}' is not a number") from None
    if not 0 <= v <= hi:
        raise AsmError(f"{where}: {v} is outside 0..{hi}")
    return v


def _reg(tok: str, where: str) -> int:
    return regmap.ADDR[tok] if tok in regmap.ADDR else _int(tok, where, 15)


def _op(op: str, args: list[str], where: str) -> int:
    def nargs(k: int) -> None:
        if len(args) != k:
            raise AsmError(f"{where}: {op} takes {k} argument(s)")

    if op == "write":
        nargs(2)
        reg, data = _reg(args[0], where), _int(args[1], where, 0xFFFF)
        if reg == regmap.TEST_CTRL_0:
            why = regmap.test_ctrl_violation(data)
            if why:
                raise AsmError(f"{where}: TEST_CTRL_0 = 0x{data:04X} {why}")
        return word(OP_SPI, reg, data)
    if op == "read":
        nargs(1)
        return word(OP_SPI, 0x10 | _reg(args[0], where))
    if op == "waitc":
        nargs(1)
        return word(OP_WAITC, 0, _int(args[0], where, 0xFFFF))
    if op == "capture":
        nargs(1)
        return word(OP_CAPT, 0, _int(args[0], where, 0xFFFF))
    if op == "loopback":
        nargs(1)
        return word(OP_LOOP, 0, _int(args[0], where, 1))
    if op in ("stream", "reset", "halt"):
        nargs(0)
        return word({"stream": OP_STREAM, "reset": OP_RESET, "halt": OP_HALT}[op])
    raise AsmError(f"{where}: unknown op '{op}'")


def _lines(path: Path, depth: int = 0):
    if depth > 4:
        raise AsmError(f"{path}: includes nested too deep")
    for n, raw in enumerate(path.read_text().splitlines(), 1):
        toks = raw.split("#", 1)[0].split()
        if toks and toks[0] == "include":
            if len(toks) != 2:
                raise AsmError(f"{path.name}:{n}: include takes one file")
            yield from _lines(path.parent / toks[1], depth + 1)
        elif toks:
            yield f"{path.name}:{n}", toks


def parse(path: Path) -> dict[int, tuple[str, list[int]]]:
    """Program number to (name, ROM words)."""
    programs: dict[int, tuple[str, list[int]]] = {}
    cur: list[int] | None = None
    tst = regmap.RESET[regmap.TEST_CTRL_0]      # what the chip holds, for the core mux transitions
    for where, toks in _lines(Path(path)):
        op, args = toks[0], toks[1:]
        if op == "reset":
            tst = regmap.RESET[regmap.TEST_CTRL_0]
        if op == "program":
            if len(args) != 2:
                raise AsmError(f"{where}: program takes a number and a name")
            num = _int(args[0], where, N_PROGRAMS - 1)
            if num in programs:
                raise AsmError(f"{where}: program {num} defined twice")
            cur = []
            programs[num] = (args[1], cur)
            tst = regmap.RESET[regmap.TEST_CTRL_0]
        elif cur is None:
            raise AsmError(f"{where}: '{op}' outside a program")
        else:
            w = _op(op, args, where)
            cur.append(w)
            if w >> 28 == OP_SPI and (w >> 16) & 0x1F == regmap.TEST_CTRL_0:
                why = regmap.test_ctrl_transition(tst, w & 0xFFFF)
                if why:
                    raise AsmError(f"{where}: TEST_CTRL_0 0x{tst:04X} to 0x{w & 0xFFFF:04X} {why}")
                tst = w & 0xFFFF
    for num, (name, words) in programs.items():
        last = words[-1] if words else None
        forever = last is not None and last >> 28 == OP_CAPT and last & 0xFFFF == 0
        if last is None or not (last >> 28 == OP_HALT or forever):
            raise AsmError(f"program {num} {name} does not end in halt or capture 0")
    return programs


def assemble(programs: dict[int, tuple[str, list[int]]]) -> list[int]:
    rom = [HALT_PC] * N_PROGRAMS + [word(OP_HALT)]
    for num in sorted(programs):
        rom[num] = len(rom)
        rom.extend(programs[num][1])
    if len(rom) > ROM_DEPTH:
        raise AsmError(f"the programs need {len(rom)} ROM words, the ROM has {ROM_DEPTH}")
    return rom + [word(OP_HALT)] * (ROM_DEPTH - len(rom))


def main(argv: list[str]) -> int:
    if argv[1:] == ["--self-test"]:
        return self_test()
    if len(argv) != 4 or argv[2] != "-o":
        print("usage: seqasm.py <programs.seq> -o <seq.mem> | --self-test")
        return 2
    try:
        progs = parse(Path(argv[1]))
        rom = assemble(progs)
    except AsmError as e:
        print(f"seqasm: {e}")
        return 1
    Path(argv[3]).write_text("".join(f"{w:08x}\n" for w in rom))
    used = HALT_PC + 1 + sum(len(w) for _, w in progs.values())
    print(f"seqasm: {len(progs)} programs, {used} of {ROM_DEPTH} ROM words, into {argv[3]}")
    return 0


def self_test() -> int:
    here = Path(__file__).resolve().parent
    progs = parse(here / "programs.seq")
    rom = assemble(progs)
    assert len(rom) == ROM_DEPTH
    assert set(progs) == set(range(8)), sorted(progs)
    assert rom[0] == 17 and rom[8] == HALT_PC and rom[HALT_PC] == 0
    assert rom[rom[0]] == word(OP_LOOP, 0, 1)

    with tempfile.TemporaryDirectory() as tmp:
        def bad(body: str, needle: str) -> None:
            p = Path(tmp) / "t.seq"
            p.write_text(body)
            try:
                parse(p)
            except AsmError as e:
                assert needle in str(e), str(e)
                return
            raise AssertionError(f"assembled: {body!r}")

        bad("program 0 x\n  write TEST_CTRL_0 0x0000\n  halt\n", "t.seq:2: TEST_CTRL_0 = 0x0000 drops")
        bad("program 0 x\n  write TEST_CTRL_0 0x0700\n  halt\n", "bit 9")
        bad("program 0 x\n  write TEST_CTRL_0 0x05C0\n  halt\n", "bits 7:6")
        bad("program 0 x\n  read 5\n", "does not end")
        bad("  halt\n", "outside a program")
        # the core test mux: one integrator at a time, no page 11, and through neutral between two nodes
        bad("program 0 x\n  write TEST_CTRL_0 0x0555\n  halt\n", "more than one integrator")
        bad("program 0 x\n  write TEST_CTRL_0 0x0530\n  halt\n", "page 11")
        bad("program 0 x\n  write TEST_CTRL_0 0x0591\n  write TEST_CTRL_0 0x0592\n  halt\n", "without going through neutral")
        bad("program 0 x\n  write TEST_CTRL_0 0x05A0\n  write TEST_CTRL_0 0x0591\n  halt\n", "without going through neutral")
        fine = Path(tmp) / "fine.seq"
        fine.write_text("program 1 z\n  write TEST_CTRL_0 0x0591\n  write TEST_CTRL_0 0x0580\n  write TEST_CTRL_0 0x0592\n"
                        "  reset\n  write TEST_CTRL_0 0x0594\n  reset\n  write TEST_CTRL_0 0x05A0\n  halt\n")
        parse(fine)
        ok = Path(tmp) / "ok.seq"
        ok.write_text("program 3 y\n  write TEST_CTRL_0 0xDD00\n  capture 0\n")
        assert assemble(parse(ok))[3] == 17
    print("OK: seqasm self-test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
