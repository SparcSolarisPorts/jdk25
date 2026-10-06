#!/usr/bin/env python3
"""Check the emitted helper call sequences in a semantic SPARC model.
This does not validate instruction encodings, HotSpot compilation, or hardware.
Run with the repository's macroAssembler_sparc.cpp path as the sole argument.
"""
import random
import re
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text()
constants = {
    'oopDesc::mark_offset_in_bytes()': 0,
    'BasicLock::object_monitor_cache_offset_in_bytes()': 0,
    'in_bytes(JavaThread::lock_stack_top_offset())': 32,
    'LockStack::start_offset()': 64,
    'LockStack::end_offset()': 128,
    'markWord::lock_mask_in_place': 3,
    'markWord::unlocked_value': 1,
    'oopSize': 8,
}
registers = {'G0', 'G2_thread', 'box', 'obj', 'mark', 'tmp'}

def split_args(text):
    result = []; depth = 0; start = 0
    for i, c in enumerate(text):
        if c == '(': depth += 1
        if c == ')': depth -= 1
        if c == ',' and depth == 0:
            result.append(text[start:i].strip()); start = i + 1
    return result + [text[start:].strip()]

def program(kind, cache, debug):
    begin = source.index('void MacroAssembler::lightweight_' + kind + '(')
    end = source.index('\n}\n', begin)
    lines = source[begin:end].splitlines()[2:]
    ops = []; labels = {}; skip = False
    for line in lines:
        line = line.split('//')[0].strip()
        if line.startswith('if (UseObjectMonitorTable)'): skip = not cache; continue
        if line.startswith('if (DiagnoseSyncOnValueBasedClasses'): skip = True; continue
        if line == '}': skip = False; continue
        if skip: continue
        if line.startswith('DEBUG_ONLY('):
            if not debug: continue
            line = line[len('DEBUG_ONLY('):-1]
        line = line.replace('delayed()->', '')
        m = re.fullmatch(r'(\w+)\((.*)\);', line)
        if not m: continue
        op, args = m.groups()
        if op.startswith('assert'): continue
        args = split_args(args) if args else []
        if op == 'bind': labels[args[0]] = len(ops)
        else: ops.append((op, args))
    labels['slow'] = len(ops) + 1
    return ops, labels

def execute(code, stack, header, injected):
    ops, labels = code
    r = dict(G0=0, G2_thread=0x10000, box=0x30000, obj=0x20000, mark=0, tmp=0)
    mem = {r['obj']: header, r['box']: 123, r['G2_thread']+32: 64+8*len(stack), r['G2_thread']+56: 0xdead}
    for i in range(8): mem[r['G2_thread']+64+8*i] = stack[i] if i < len(stack) else 0
    def val(s):
        if s in registers: return r[s]
        if s in constants: return constants[s]
        return int(s)
    def setr(s, value):
        if s != 'G0': r[s] = value & ((1 << 64) - 1)
    cmp = (0, 0); pc = 0; pending = None; steps = 0
    while pc < len(ops):
        steps += 1
        assert steps < 200, 'loop in emitted sequence'
        op, a = ops[pc]; branch = None
        if op in ('ld_ptr', 'lduw'):
            value = mem[val(a[0])+val(a[1])]
            setr(a[2], value if op == 'ld_ptr' else value & 0xffffffff)
        elif op in ('st_ptr', 'st'):
            value = val(a[0]); mem[val(a[1])+val(a[2])] = value if op == 'st_ptr' else value & 0xffffffff
        elif op in ('add', 'sub', 'and3', 'andn', 'or3', 'andcc'):
            x,y = val(a[0]),val(a[1])
            z = {'add':lambda:x+y, 'sub':lambda:x-y, 'and3':lambda:x&y,
                 'andn':lambda:x&~y, 'or3':lambda:x|y, 'andcc':lambda:x&y}[op]()
            setr(a[2],z)
            if op == 'andcc': cmp = (z,0)
        elif op == 'cmp': cmp = (val(a[0]),val(a[1]))
        elif op == 'cas_ptr':
            if injected: mem[val(a[0])] = (mem[val(a[0])] & ~3) | 2
            old = mem[val(a[0])]
            if old == val(a[1]): mem[val(a[0])] = val(a[2])
            setr(a[2],old)
        elif op == 'brx':
            x,y = cmp
            taken = {'Assembler::equal':x==y, 'Assembler::notEqual':x!=y,
                     'Assembler::notZero':x!=y, 'Assembler::greaterEqualUnsigned':x>=y,
                     'Assembler::lessEqualUnsigned':x<=y}[a[0]]
            if taken: branch = labels[a[-1]]
        elif op not in ('nop','membar'): raise AssertionError('unmodeled instruction '+op)
        next_pc = pending if pending is not None else pc+1
        pending = branch
        pc = next_pc
    success = pc == len(ops)
    top = mem[r['G2_thread']+32]
    after = [mem[r['G2_thread']+i] for i in range(64,top,8)]
    assert r['obj'] == 0x20000 and r['box'] == 0x30000 and r['G2_thread'] == 0x10000
    return success, after, mem[0x20000]

rng = random.Random(25)
checks = 0
for cache in (False,True):
    for debug in (False,True):
        for kind in ('lock','unlock'):
            code = program(kind,cache,debug)
            for n in range(20000):
                stack = [rng.choice([0x20000,0x40000,0x50000]) for _ in range(rng.randrange(9))]
                bits = rng.randrange(3); header = (rng.getrandbits(48)<<2)|bits
                injected = bool(rng.randrange(2))
                recursive = bool(stack) and stack[-1] == 0x20000
                if kind == 'lock':
                    expected = len(stack)<8 and (recursive or (bits==1 and not injected))
                    target = stack+[0x20000] if expected else stack
                else:
                    recursive = len(stack)>=2 and stack[-2:]==[0x20000]*2
                    expected = bool(stack) and stack[-1]==0x20000 and (recursive or (bits==0 and not injected))
                    target = stack[:-1] if expected else stack
                success, after, mark = execute(code,stack,header,injected)
                assert (success,after)==(expected,target), (kind,stack,bits,injected,success,after)
                if success and not recursive:
                    assert mark == ((header & ~3) | (0 if kind=='lock' else 1))
                checks += 1
print('PASS',checks,'emitted-sequence scenarios (semantic model only)')
