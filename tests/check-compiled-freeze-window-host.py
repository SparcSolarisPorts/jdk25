#!/usr/bin/env python3
"""Check the actual compiled freeze copy-start function, with both arch branches."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
stage=root if (root/'src/hotspot').exists() else root.parent/'verify'
s=(stage/'src/hotspot/share/runtime/continuationHelper.inline.hpp').read_text()
a=s.index('inline intptr_t* ContinuationHelper::NonInterpretedFrame::frame_top(const frame& f, int callee_argsize, bool callee_interpreted)')
i=s.index('{',a)+1;n=1
while n:
 n+=(s[i]=='{')-(s[i]=='}');i+=1
function=s[a:i]
model=r'''
#include <cstdint>
#include <cstring>
#include <cassert>
#include <cstdio>
struct frame {intptr_t* p;intptr_t* unextended_sp()const{return p;}};
struct ContinuationHelper {struct NonInterpretedFrame {static intptr_t* frame_top(const frame&,int,bool);};};
'''
checks=r'''
int main(){
 intptr_t stack[512],heap[512];
 for(int args=0;args<=96;args++)for(int interpreted=0;interpreted<2;interpreted++){
  for(int j=0;j<512;j++){stack[j]=0x50000+j;heap[j]=0;}
  frame f{stack+128};
  intptr_t* top=ContinuationHelper::NonInterpretedFrame::frame_top(f,args,interpreted);
#ifdef SPARC
  assert(top==f.unextended_sp());
  // Mirror the slow-freeze copy: payload begins at heap frame top, which
  // also owns the saved registers. L5-L7/I0 are live oop-map locations.
  memcpy(heap,top,128*sizeof(intptr_t));
  for(int reg=0;reg<16;reg++)assert(heap[reg]==f.unextended_sp()[reg]);
#else
  (void)heap;
  assert(top==f.unextended_sp()+(interpreted?0:args));
#endif
 }
 puts("PASS: actual compiled freeze copy-start, 194 argument/callee cases");
}
'''
with tempfile.TemporaryDirectory(prefix='sparc-compiled-freeze-') as tmp:
 d=Path(tmp);(d/'check.cpp').write_text(model+function+checks)
 for arch in (['-DSPARC'],[]):
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',*arch,str(d/'check.cpp'),'-o',str(d/'check')],check=True)
  subprocess.run([str(d/'check')],check=True)
