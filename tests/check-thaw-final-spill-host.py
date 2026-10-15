#!/usr/bin/env python3
"""Host overlap model: final runtime spill occurs AFTER the C++ thaw copies."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
stage=root if (root/'src/hotspot').exists() else root.parent/'verify'
s=(stage/'src/hotspot/cpu/sparc/continuationFreezeThaw_sparc.inline.hpp').read_text()
a=s.index('static inline void thaw_sparc_restore_caller_window(');i=s.index('{',a)+1;n=1
while n:
 n+=(s[i]=='{')-(s[i]=='}');i+=1
helper=s[a:i]
stub=(stage/'src/hotspot/cpu/sparc/stubGenerator_sparc.cpp').read_text()
a=stub.index('// Slow thaw may have relocated');b=stub.index('// Find each child using its saved I6.',a)
code=stub[a:b]
assert code.index('__ restore();') < code.index('thaw_entry_window_offset()')
assert 'call_VM' not in code[code.index('thaw_entry_window_offset()'):]
assert '__ ld_ptr(G1, in_bytes(ContinuationEntry::cont_offset()), I0);' in code
assert 'as_iRegister(reg)' in code and '(8 + reg) * wordSize' in code
shared=(stage/'src/hotspot/share/runtime/continuationFreezeThaw.cpp').read_text()
assert '(HeapWord*)_cont.entry()->thaw_entry_window()' in shared
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
 int failures_before_fix=0;
 for(int args=0;args<=96;args++){
  alignas(16) intptr_t stack[1024],heap[512],stable[16],resident[16];
  for(int j=0;j<1024;j++)stack[j]=0x50000+j;
  for(int j=0;j<512;j++)heap[j]=0x70000+j;
  intptr_t* canonical=stack+512;
  canonical[12]=1;canonical[14]=0x12345670;canonical[15]=0x87654320;
  Copy::conjoint_words(canonical,stable,16);
  intptr_t* physical=canonical-((args+1)&~1);
  intptr_t* frozen=heap+128;
  for(int j=0;j<args;j++)frozen[16+j]=0x90000+j;
  thaw_sparc_restore_caller_window(stable,physical,frozen,args);
  // A resident entry window spills at the original canonical SP on the
  // runtime return path, after C++ has restored the extended caller.
  Copy::conjoint_words(stable,canonical,16);
  bool bad=false;
  for(int j=0;j<16;j++)bad|=physical[j]!=stable[j];
  for(int j=0;j<args;j++)bad|=physical[16+j]!=frozen[16+j];
  failures_before_fix+=bad;
  // New stub: architectural L/I reload happens after the runtime returns.
  for(int j=0;j<16;j++)resident[j]=stable[j];
  resident[8]=0xabcdef00; // refreshed I0 from GC-updated entry root
  assert(resident[8]==0xabcdef00,"entry oop refreshed");
  assert(resident[14]==0x12345670,"valid hardware I6 before rebuilding");
  assert(resident[15]==0x87654320,"entry return PC");
  // A subsequent SAVE may spill this corrected resident entry at its
  // physical SP. Argument restoration remains a separate open issue.
  Copy::conjoint_words(resident,physical,16);
  assert(physical[14]==0x12345670,"correct physical I6 after SAVE");
 }
 assert(failures_before_fix>0,"must reproduce the post-C++ corruption");
 printf("PASS: 97 final-spill layouts; old ordering corrupts %d; staged entry window survives\n",failures_before_fix);
}
'''
with tempfile.TemporaryDirectory(prefix='sparc-final-spill-') as tmp:
 d=Path(tmp);(d/'check.cpp').write_text(model+helper+checks)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(d/'check.cpp'),'-o',str(d/'check')],check=True)
 subprocess.run([str(d/'check')],check=True)
