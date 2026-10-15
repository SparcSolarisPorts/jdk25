#!/usr/bin/env python3
"""Compile the actual frame-membership predicate with relocated-entry cases."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
stage=root if (root/'src/hotspot').exists() else root.parent/'verify'
s=(stage/'src/hotspot/share/runtime/continuation.cpp').read_text()
a=s.index('bool Continuation::is_frame_in_continuation(const ContinuationEntry* entry, const frame& f)');i=s.index('{',a)+1;n=1
while n:
 n+=(s[i]=='{')-(s[i]=='}');i+=1
fn=s[a:i]
freeze=(stage/'src/hotspot/share/runtime/continuationFreezeThaw.cpp').read_text()
a=freeze.index('    frame senderf = sender<FKind>(f);');b=freeze.index('freeze_result result = recurse_freeze(senderf',a)
assert freeze[a:b].index('Continuation::is_continuation_enterSpecial(senderf)') < freeze[a:b].index('return finalize_freeze(f, caller, argsize);')
model=r'''
#include <cstdint>
#include <cassert>
#include <cstdio>
struct frame {intptr_t *s,*u;bool special;intptr_t* sp()const{return s;}intptr_t* unextended_sp()const{return u;}};
struct ContinuationEntry {intptr_t* s;intptr_t* entry_sp()const{return s;}};
static bool is_sp_in_continuation(const ContinuationEntry* e,intptr_t* s){return e->entry_sp()>s;}
struct Continuation {
 static bool is_continuation_enterSpecial(const frame& f){return f.special;}
 static bool is_frame_in_continuation(const ContinuationEntry*,const frame&);
};
'''
checks=r'''
int main(){
 intptr_t stack[1024];ContinuationEntry entry{stack+512};
 for(int shift=0;shift<=128;shift+=2){
  frame own{entry.s-shift,entry.s,true};
#ifdef SPARC
  assert(!Continuation::is_frame_in_continuation(&entry,own));
#else
  assert(Continuation::is_frame_in_continuation(&entry,own)==(shift>0));
#endif
  // A nested entry belongs inside the outer continuation. Genuine native
  // wrappers keep ordinary membership so pinning checks can still see them.
  frame nested{stack+128,stack+256,true};
  frame native_wrapper{stack+128,stack+128,false};
  assert(Continuation::is_frame_in_continuation(&entry,nested));
  assert(Continuation::is_frame_in_continuation(&entry,native_wrapper));
  frame carrier{stack+600,stack+600,false};
  assert(!Continuation::is_frame_in_continuation(&entry,carrier));
 }
 puts("PASS: actual entry membership; 65 shifts, nested entries, native wrappers and carrier frames");
}
'''
with tempfile.TemporaryDirectory(prefix='sparc-entry-boundary-') as tmp:
 d=Path(tmp);(d/'check.cpp').write_text(model+fn+checks)
 for arch in (['-DSPARC'],[]):
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',*arch,str(d/'check.cpp'),'-o',str(d/'check')],check=True)
  subprocess.run([str(d/'check')],check=True)
