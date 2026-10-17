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
mask64 = (1 << 64) - 1

def signed32_return(value):
    value &= 0xffffffff
    return (value if value < 0x80000000 else value - (1 << 32)) & mask64

for name, load, patterns in [
    ('32', 'ldsw', [0, 1, 0x7fffffff, 0x80000000, 2882382797, 0xffffffff]),
    ('N', 'ldx', [0, 1, 0x7fffffffffffffff, 0x8000000000000000, 0xf123456789abcdef, mask64]),
]:
    fault = labels['_SafeFetch%s_fault' % name]
    assert code[fault // 4].startswith(load + ' '), 'fault symbol must name the correct signed/native load'
    for value in patterns:
        for bad in (False, True):
            for default in (0, 1, -1, -1412584499):
                pc = labels['SafeFetch%s_impl' % name]
                npc, ret = pc + 4, 0x10000
                o0, o1, faults = 0x4000, default & mask64, 0
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
                            npc = pc + 4
                            faults += 1
                            continue
                        # ldsw writes a sign-extended 64-bit register, ldx preserves all bits.
                        o0 = signed32_return(value) if load == 'ldsw' else value
                    elif insn == 'mov %o1, %o0':
                        o0 = o1
                    else:
                        assert insn == 'nop', insn
                    pc, npc = npc, target
                assert pc == ret
                want = (default & mask64) if bad else (signed32_return(value) if name == '32' else value)
                assert o0 == want
                assert faults == int(bad)
                cases += 1
assert signed32_return(2882382797) == 18446744072296967117
print('PASS: %d actual-source SafeFetch signed ABI/load/return/recovery cases (host model)' % cases)
