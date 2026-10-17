#!/usr/bin/env python3
"""Model the actual SPARC SafeFetch assembly and its precise PC recovery ABI.
This is a host control-flow check, not SPARC execution.
"""
from pathlib import Path
import sys
root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
source = root / 'src/hotspot/os_cpu/solaris_sparc/safefetch_solaris_sparc.S'
code, labels = [], {}
for line in source.read_text().splitlines():
    line = line.split('#', 1)[0].strip()
    if not line or line.startswith('.'):
        continue
    if line.endswith(':'):
        labels[line[:-1]] = len(code) * 4
    else:
        code.append(line)

cases = 0
for name, load, value in [('32', 'ld', 0xf1234567), ('N', 'ldx', 0xf123456789abcdef)]:
    fault = labels['_SafeFetch%s_fault' % name]
    assert code[fault // 4].startswith(load + ' '), 'fault symbol must name the load'
    for bad in (False, True):
        for default in (0, 1, -1, 0x12345678):
            pc = labels['SafeFetch%s_impl' % name]
            npc, ret = pc + 4, 0x10000
            o0, o1, faults = 0x4000, default, 0
            for _ in range(16):
                if pc == ret:
                    break
                insn = code[pc // 4]
                target = npc + 4
                if insn == 'retl':
                    target = ret
                elif insn.startswith(load + ' '):
                    if bad:
                        assert pc == fault, 'saved fault PC would not match shared handler'
                        pc = labels['_SafeFetch%s_continuation' % name]
                        npc = pc + 4  # os::Posix::ucontext_set_pc restores both.
                        faults += 1
                        continue
                    o0 = value
                elif insn == 'mov %o1, %o0':
                    o0 = o1
                else:
                    assert insn == 'nop', insn
                pc, npc = npc, target
            assert pc == ret
            assert o0 == (default if bad else value)
            assert faults == int(bad)
            cases += 1
print('PASS: %d actual-source SafeFetch load/return/recovery cases (host model)' % cases)
