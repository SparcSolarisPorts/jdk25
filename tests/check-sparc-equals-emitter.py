#!/usr/bin/env python3
"""Host interpreter of the actual SPARC equality emitter; no native execution."""
from pathlib import Path
import re
root = Path(__file__).resolve().parent.parent
source = root / 'src/hotspot/cpu/sparc/c2_MacroAssembler_sparc.cpp'
if not source.exists():
    source = root.parent / 'verify/src/hotspot/cpu/sparc/c2_MacroAssembler_sparc.cpp'
s = source.read_text()
s = s[s.index('  // Compact headers can place'):]
s = s[:s.index('\n}', s.index('  bind(Ldone);'))]
s = re.sub(r'//[^\n]*', '', s)
ops = []
labels = {}
for line in s.splitlines():
    line = line.strip()
    if not line:
        continue
    m = re.fullmatch(r'(?:delayed\(\)->)?(\w+)\((.*)\);', line)
    if not m:
        raise AssertionError('Unparsed emitter: ' + line)
    op, args = m.groups()
    args = [re.sub(r'^target\((.*)\)$', r'\1', x.strip()) for x in args.split(',')]
    if op == 'bind':
        labels[args[0]] = len(ops)
    else:
        ops.append((op, args))

def run(offset1, offset2, n, mismatch):
    mem = bytearray(4096)
    a, b = 256 + offset1, 2048 + offset2
    for i in range(n):
        mem[a+i] = mem[b+i] = (i*37+19)&255
    if mismatch is not None:
        mem[b+mismatch] ^= 1
    r = dict(ary1=a, ary2=b, limit=n, tmp=0, result=0, G0=0)
    cc = 0
    loads8 = 0
    def val(x):
        return r[x] if x in r else int(x)
    def put(x, v):
        if x != 'G0': r[x] = v
    def cond(c):
        return {'equal':cc==0,'zero':cc==0,'notEqual':cc!=0,'notZero':cc!=0,
                'less':cc<0,'positive':cc>0}[c.split('::')[-1]]
    def execute(op,args):
        nonlocal cc,loads8
        x=args
        if op=='nop': return
        if op in ('ldx','lduw','ldub'):
            size={'ldx':8,'lduw':4,'ldub':1}[op]; addr=val(x[0])+val(x[1])
            assert addr%size==0, (op,addr,offset1,offset2,n,mismatch)
            if size==8: loads8+=1
            put(x[2],int.from_bytes(mem[addr:addr+size],'big')); return
        if op=='cmp': cc=val(x[0])-val(x[1]);return
        if op=='clr': put(x[0],0);return
        if op=='mov': put(x[1],val(x[0]));return
        if op=='neg': put(x[1],-val(x[0]));return
        if op in ('inccc','deccc'):
            dest=x[0]; put(dest,val(dest)+(val(x[1]) if len(x)>1 else 1)*(1 if op=='inccc' else -1));cc=val(dest);return
        if op=='movcc':
            if cond(x[0]):put(x[-1],val(x[-2]))
            return
        av,bv=val(x[0]),val(x[1])
        value={'or3':lambda:av|bv,'and3':lambda:av&bv,'andcc':lambda:av&bv,
               'add':lambda:av+bv,'sub':lambda:av-bv,'sll':lambda:av<<(bv&31),
               'srlx':lambda:(av&((1<<64)-1))>>(bv&63)}[op]()
        put(x[2],value)
        if op=='andcc':cc=value
    pc=0;steps=0
    while pc<len(ops):
        steps+=1; assert steps<1000
        op,args=ops[pc]
        if op in ('br','brx','ba','cmp_zero_and_br'):
            if op=='ba':taken=True;annul=False;label=args[0]
            elif op=='cmp_zero_and_br':
                cc=val(args[1]);taken=cond(args[0]);label=args[2];annul=args[3]=='true'
            else:taken=cond(args[0]);annul=args[1]=='true';label=args[-1]
            if not annul or taken:execute(*ops[pc+1])
            pc=labels[label] if taken else pc+2
        else:
            execute(op,args);pc+=1
    assert r['result']==int(mismatch is None), (offset1,offset2,n,mismatch,r)
    if offset1==offset2==4 and n>=12 and (mismatch is None or mismatch>=4):assert loads8>0, 'compact aligned bulk path lost'

cases=0
for a in range(8):
    for b in range(8):
        for n in range(1,66):
            for mismatch in dict.fromkeys((None,0,n//2,n-1)):
                run(a,b,n,mismatch);cases+=1
print(f'PASS: {cases} extracted equality-emitter cases, all alignments, prefix/bulk/tail mismatches')
