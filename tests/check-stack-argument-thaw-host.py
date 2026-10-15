#!/usr/bin/env python3
"""Check actual SPARC caller-window/argument restoration against a host layout model."""
from pathlib import Path
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
p = root/'src/hotspot/cpu/sparc/continuationFreezeThaw_sparc.inline.hpp'
if not p.exists(): p = root.parent/'verify/src/hotspot/cpu/sparc/continuationFreezeThaw_sparc.inline.hpp'
s = p.read_text(); a = s.index('static inline void thaw_sparc_restore_caller_window(')
i = s.index('{', a) + 1; depth = 1
while depth:
    depth += (s[i] == '{') - (s[i] == '}'); i += 1
helper = s[a:i]
model = r'''
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cstdio>
using HeapWord = intptr_t;
#define assert(c, ...) do { if (!(c)) std::abort(); } while (0)
struct frame { static constexpr int register_save_words = 16; };
struct VMRegImpl { static constexpr int slots_per_word = 2; };
struct SharedRuntime { static int out_preserve_stack_slots() { return 32; } };
struct Copy { static void conjoint_words(HeapWord* f, HeapWord* t, int n) {
 std::memmove(t, f, n * sizeof(HeapWord));
} };
'''
checks = r'''
int main() {
 for (int args=0; args<=96; args++) {
  for (int copied_overlap : {0, 1}) {
   intptr_t stack[1024], heap[1024], saved[16];
   for(int i=0;i<1024;i++){stack[i]=0x50000+i;heap[i]=0x70000+i;}
   intptr_t* canonical=stack+512;
   canonical[12]=1; // Reported crash: old I4 misread as shifted I6.
   canonical[14]=0x12345670;canonical[15]=0x87654320;
   Copy::conjoint_words(canonical,saved,16);
   int extension=(args+1)&~1;
   intptr_t* physical=canonical-extension;
   intptr_t* heap_caller=heap+512;
   for(int j=0;j<args;j++)heap_caller[16+j]=0x90000+j;
   if(copied_overlap) { // Slow path moved the window before the payload copy.
    Copy::conjoint_words(saved,physical,16);
    for(int j=0;j<args;j++)physical[j]=heap_caller[j];
   } else if(args==1) {
    assert(physical[14]==1,"reproduce original bad FP");
   }
   thaw_sparc_restore_caller_window(saved,physical,heap_caller,args);
   for(int j=0;j<16;j++)assert(physical[j]==saved[j],"saved window");
   for(int j=0;j<args;j++)assert(physical[16+j]==0x90000+j,"ABI argument data");
   for(int j=24;j<64;j++)assert(canonical[j]==0x50000+512+j,"entry metadata unchanged");
  }
 }
 std::puts("PASS: actual helper, 0..96 argument words, bulk-copy overlap, I6/I7 and entry metadata");
}
'''
model = '#include <initializer_list>\n'+model
with tempfile.TemporaryDirectory(prefix='sparc-stack-args-') as tmp:
    d=Path(tmp); (d/'check.cpp').write_text(model+helper+checks)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(d/'check.cpp'),'-o',str(d/'check')],check=True)
    subprocess.run([str(d/'check')],check=True)
