# Host model; does not execute SPARC machine code. Run from source-tree root.
from pathlib import Path
import re
src=Path('src/hotspot/cpu/sparc/stubGenerator_sparc.cpp').read_text()
a=src.index('    if (return_barrier) {',src.index('  address generate_cont_thaw(Continuation::thaw_kind kind)'))
b=src.index('    // Rebuild the hardware window chain',a)
body=src[a:b]
body=re.sub(r'#ifdef ASSERT.*?#endif','',body,flags=re.S)
body=re.sub(r'//[^\n]*','',body)
class W:
 def __init__(self,sp,fp):
  self.L=[0]*8;self.I=[0]*8;self.O=[0]*8;self.O[6]=sp;self.I[6]=fp

def generate(barrier):
 # This generator region has only static return_barrier conditions and labels.
 tokens=re.split(r'([{}])',body);states=[True];out='';pending=True
 for t in tokens:
  if t=='{':states.append(states[-1] and pending);pending=True
  elif t=='}':states.pop()
  else:
   m=re.search(r'if\s*\(return_barrier\)\s*$',t)
   if m:
    if states[-1]:out+=t[:m.start()]
    pending=barrier
   elif re.search(r'else\s*$',t):pending=not barrier
   elif states[-1]:out+=t
 calls=re.findall(r'__\s+(\w+)\((.*?)\)\s*;',out,re.S)
 labels={args.strip():i for i,(name,args) in enumerate(calls) if name=='bind'}
 return calls,labels

def run(barrier,size,extension,extra):
 BIAS=2047;entry=0x1000000;bottom=entry-extension;top=entry-size
 thread=0x100138310;result=0x1020304050607080;fp_result=0x3ff0123456789abc
 mem={};g={'G1':0,'G2_thread':thread,'G3_scratch':0,'G4_scratch':0,'G5':0};F0=fp_result
 w=W(entry-BIAS,entry+288-BIAS);w.I[0]=0x7ffd11110;w.I[7]=0x70806000;w.O[0]=result
 windows=[w]
 def get(x):
  x=x.strip()
  if x in g:return g[x]
  if x=='SP':return windows[-1].O[6]
  if x=='FP':return windows[-1].I[6]
  if re.fullmatch('[ILO][0-7]',x):return getattr(windows[-1],x[0])[int(x[1])]
  return {'STACK_BIAS':BIAS,'result_offset':176,'scratch_bytes + STACK_BIAS':192+BIAS,
   '(int)ContinuationEntry::size()':288,'return_barrier ? 1 : 0':int(barrier),
   '(int)kind':int(barrier),'in_bytes(JavaThread::cont_entry_offset())':0x100,
   'in_bytes(ContinuationEntry::thaw_bottom_offset())':184,
   'STACK_BIAS + result_offset':BIAS+176}.get(x,int(x) if re.fullmatch(r'-?\d+',x) else None)
 def put(x,v):
  x=x.strip()
  if x in g:g[x]=v
  elif x=='SP':windows[-1].O[6]=v
  elif x=='FP':windows[-1].I[6]=v
  else:getattr(windows[-1],x[0])[int(x[1])]=v
 def spill(w):
  for i,v in enumerate(w.L+w.I):mem[w.O[6]+BIAS+i*8]=v
 def save(delta):
  parent=windows[-1];spill(parent)
  child=W(parent.O[6]+delta,parent.O[6]);child.I=parent.O.copy();windows.append(child)
 def restore():
  child=windows.pop();parent=windows[-1];parent.O=child.I.copy()
  # Force a Solaris register-window underflow/refill at every RESTORE.
  p=parent.O[6]+BIAS
  parent.L=[mem[p+i*8] for i in range(8)]
  parent.I=[mem[p+(8+i)*8] for i in range(8)]
 mem[thread+0x100]=entry;mem[entry+184]=bottom
 # Force the return-barrier unwind through additional caller windows.
 for _ in range(extra):save(-192)
 windows[-1].O[0]=result
 code,labels=generate(barrier);pc=0;count=0;calls=0
 while pc<len(code):
  count+=1;assert count<1000
  name,argstr=code[pc];pc+=1
  args=[x.strip() for x in argstr.split(',')]
  if name=='mov':put(args[1],get(args[0]))
  elif name=='set':put(args[1],get(args[0]))
  elif name in ('sub','add','and3'):
   x,y=get(args[0]),get(args[1]);assert x is not None and y is not None,(name,args)
   put(args[2],x-y if name=='sub' else x+y if name=='add' else x&y)
  elif name=='clr':put(args[0],0)
  elif name=='save_frame':save(-(22+get(args[0]))*8)
  elif name=='save':save(get(args[1]))
  elif name=='restore':restore()
  elif name=='flushw':
   for win in windows[:-1]:spill(win)
  elif name=='ld_ptr':put(args[2],mem[get(args[0])+get(args[1])])
  elif name=='stf':mem[get(args[2])+get(args[3])]=F0
  elif name=='ldf':F0=mem[get(args[1])+get(args[2])]
  elif name=='cmp_and_brx_short':
   if get(args[0])==get(args[1]):pc=labels[args[-1]]
  elif name=='br_notnull_short':
   if get(args[0])!=0:pc=labels[args[-1]]
  elif name=='ba':pc=labels[args[0]]
  elif name in ('bind','delayed','nop','total_frame_size_in_bytes'):pass
  elif name=='call_VM_leaf':
   calls+=1;cur=windows[-1];cur.L[7]=g['G2_thread'];spill(cur)
   if calls==2:
    assert cur.O[6]+BIAS+192<=top,'native save area overlaps Java restore region'
    saved=[mem[entry+i*8] for i in range(16)]
    for i in range(size//8):mem[top+i*8]=0x900000+i
    for i,v in enumerate(saved):mem[bottom+i*8]=v
   # C clobbers all volatile globals/results/F0. Restore_thread must use
   # the intact native save area, even after the Java frame copy.
   g.update({'G2_thread':0xbad,'G3_scratch':0xbad,'G4_scratch':0xbad,'G5':0xbad});F0=0xbad
   cur.L=[mem[cur.O[6]+BIAS+i*8] for i in range(8)]
   cur.I=[mem[cur.O[6]+BIAS+(8+i)*8] for i in range(8)]
   g['G2_thread']=cur.L[7];cur.O[0]=size if calls==1 else top
  elif name=='jump_to':raise AssertionError('unexpected overflow')
  else:raise AssertionError((name,argstr))
 assert calls==2 and len(windows)==1
 assert g['G2_thread']==thread
 assert g['G4_scratch']==top
 assert g['G5']==(result if barrier else 0)
 assert not barrier or F0==fp_result
 assert windows[0].I[0]==0x7ffd11110,'entry continuation argument corrupted'
 assert windows[0].O[6]+BIAS==bottom
count=0
for barrier in (False,True):
 for size in (176,320,2048,16384):
  for extension in (0,16,64,128):
   for extra in ((0,1,5) if barrier else (0,)):
    run(barrier,size,extension,extra);count+=1
print(f'PASS: {count} extracted native-call sequences, forced window refills, relocated entry and integer/FP results')
