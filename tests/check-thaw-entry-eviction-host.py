#!/usr/bin/env python3
"""Check entry eviction ordering and its effect on overlapping arguments."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
stage=root if (root/'src/hotspot').exists() else root.parent/'verify'
stub=(stage/'src/hotspot/cpu/sparc/stubGenerator_sparc.cpp').read_text()
a=stub.index('    __ save(SP, L3, SP);',stub.index('address generate_cont_thaw(Continuation::thaw_kind kind)'))
b=stub.index('                    Continuation::thaw_entry(),',a)
call=stub[a:b]
assert '__ flushw();' in call,'entry must be evicted from inside the runtime scratch window'
assert '__ restore' not in call,'entry must remain nonresident until the runtime thaw has run'
s=(stage/'src/hotspot/cpu/sparc/continuationFreezeThaw_sparc.inline.hpp').read_text()
a=s.index('static inline void thaw_sparc_restore_caller_window(');i=s.index('{',a)+1;n=1
while n:
 n+=(s[i]=='{')-(s[i]=='}');i+=1
helper=s[a:i]
model=r'''
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#define assert(c, ...) do { if (!(c)) std::abort(); } while(0)
using HeapWord=intptr_t;
struct frame {static constexpr int register_save_words=16;};
struct VMRegImpl {static constexpr int slots_per_word=2;};
struct SharedRuntime {static int out_preserve_stack_slots(){return 32;}};
struct Copy {static void conjoint_words(HeapWord* f,HeapWord* t,int n){memmove(t,f,n*sizeof(*f));}};
'''
checks=r'''
int main(){
 int old_failures=0,new_failures=0,cases=0;
 for(int args=0;args<=96;args++)for(int depth=0;depth<12;depth++)for(int evict=0;evict<2;evict++){
  alignas(16) intptr_t stack[1024],heap[512],entry[16];
  for(int i=0;i<1024;i++)stack[i]=0x50000+i;
  for(int i=0;i<512;i++)heap[i]=0x70000+i;
  intptr_t* canonical=stack+512;
  canonical[14]=0x12345670;canonical[15]=0x87654320;
  Copy::conjoint_words(canonical,entry,16);
  intptr_t* physical=canonical-((args+1)&~1);
  intptr_t* frozen=heap+128;
  for(int j=0;j<args;j++)frozen[16+j]=0x90000+j;
  // The first flush's RESTORE made entry resident again. A scratch SAVE
  // alone leaves older resident windows eligible for subsequent spilling.
  bool entry_resident=true;
  if(evict){Copy::conjoint_words(entry,canonical,16);entry_resident=false;}
  // Deep native calls may happen to evict it before the stack copy, which
  // explains why some paths can pass without the explicit flush.
  if(depth>=6&&entry_resident){Copy::conjoint_words(entry,canonical,16);entry_resident=false;}
  thaw_sparc_restore_caller_window(entry,physical,frozen,args);
  // Late spill on the runtime return path: harmful only if still resident.
  if(entry_resident)Copy::conjoint_words(entry,canonical,16);
  // v61 reloads registers, but that alone does not repair spilled arguments.
  Copy::conjoint_words(entry,physical,16);
  bool bad=false;
  for(int j=0;j<args;j++)bad|=physical[16+j]!=frozen[16+j];
  if(evict)new_failures+=bad;else old_failures+=bad;
  cases++;
 }
 assert(old_failures>0,"reproduce corrupt arguments with old ordering");
 assert(new_failures==0,"entry eviction protects restored arguments");
 printf("PASS: %d resident-window layout cases; old failures=%d, new failures=%d\n",cases,old_failures,new_failures);
}
'''
with tempfile.TemporaryDirectory(prefix='sparc-entry-eviction-') as tmp:
 d=Path(tmp);(d/'check.cpp').write_text(model+helper+checks)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(d/'check.cpp'),'-o',str(d/'check')],check=True)
 subprocess.run([str(d/'check')],check=True)
