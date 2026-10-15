#!/usr/bin/env python3
"""Exercise actual fresh-chunk allocation, argument count and explicit copy."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
stage=root if (root/'src/hotspot').exists() else root.parent/'verify'
s=(stage/'src/hotspot/share/runtime/continuationFreezeThaw.cpp').read_text()
a=s.index('    const int arg_window = callee.is_compiled_frame()');b=s.index('\n#else',a)
allocation=s[a:b]
a=s.index('  const int stack_args = f.compiled_frame_stack_argsize();');b=s.index('\n#endif',a)
copy=s[a:b]
a=s.index('      int sp = chunk->stack_size() - argsize_md;');b=s.index('      _freeze_size += overlap;',a)
reuse=s[a:b]
s=(stage/'src/hotspot/share/oops/stackChunkOop.inline.hpp').read_text()
a=s.index('inline int stackChunkOopDesc::argsize() const');i=s.index('{',a)+1;n=1
while n:
 n+=(s[i]=='{')-(s[i]=='}');i+=1
argsize=s[a:i]
model=r'''
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <vector>
#define assert(c, ...) do { if (!(c)) std::abort(); } while(0)
using HeapWord=intptr_t;
struct frame {
 static constexpr int register_save_words=16,metadata_words_at_top=0;
 intptr_t* p;int args;bool compiled=true;
 intptr_t* fp()const{return p;}int compiled_frame_stack_argsize()const{return args;}
 bool is_compiled_frame()const{return compiled;}
};
struct stackChunkOopDesc {
 std::vector<intptr_t> memory;int size,b,s;bool window=false;
 stackChunkOopDesc(int words,int md):memory(words+4,0),size(words),b(words-md),s(b){memory[words]=0x12345678;}
 bool is_empty()const{return s==b;}int stack_size()const{return size;}int bottom()const{return b;}
 intptr_t* start_address(){return memory.data();}intptr_t* end_address(){return start_address()+size;}
 bool has_sparc_arg_window()const{return window;}void set_has_sparc_arg_window(bool v){window=v;}
 void set_sp(int v){s=v;}void set_bottom(int v){b=v;}
 int argsize()const;
};
struct Cont {stackChunkOopDesc* c;stackChunkOopDesc* tail(){return c;}};
struct Copy {static void conjoint_words(HeapWord* f,HeapWord* t,int n){memmove(t,f,n*sizeof(*f));}};
'''
checks=r'''
void store(const frame& f,const frame& hf,Cont& _cont){COPY}
int main(){
 int cases=0,missing_before=0;
 for(int args=0;args<=96;args++)for(int frames=1;frames<=3;frames++){
  int _freeze_size=28*frames+args,argsize_md=args,argsize=args;
  frame callee{nullptr,args};stackChunkOopDesc* chunk=nullptr;
  auto allocate_chunk_slow=[](int size,int md){return new stackChunkOopDesc(size,md);};
  ALLOCATION
  chunk->set_has_sparc_arg_window(arg_window!=0);
  // No physical window is counted as Java arguments or native thaw bytes.
  assert(chunk->bottom()==28*frames,"bottom boundary");
  chunk->set_sp(0);
  assert(chunk->argsize()==args,"logical argument count");
  assert(_freeze_size==28*frames+args,"native thaw estimate unchanged");
  intptr_t native[256];for(int j=0;j<256;j++)native[j]=0x70000+j;
  frame f{native+32,args};frame hf{chunk->start_address()+chunk->bottom(),args};
  // Old contiguous copy reached only fp()+args: actual ABI arguments were
  // still zero, or outside the old object's allocation entirely.
  for(int j=0;j<args;j++)missing_before+=hf.fp()[16+j]!=f.fp()[16+j];
  Cont _cont{chunk};store(f,hf,_cont);
  for(int j=0;j<args;j++)assert(hf.fp()[16+j]==f.fp()[16+j],"all args retained for subsequent GC/thaw");
  assert(chunk->memory[chunk->size]==0x12345678,"allocation guard unchanged");
  // Empty-chunk reuse must recompute the trailer for a new bottom frame.
  for(int next=0;next<=args;next++){
   int argsize=next,argsize_md=next;frame callee{nullptr,next};
   REUSE
   chunk->set_sp(chunk->bottom()-1);
   assert(chunk->argsize()==next,"reused logical argument count");
   assert(chunk->bottom()+next+(next?16:0)==chunk->size,"reused physical capacity");
  }
  delete chunk;cases++;
 }
 assert(missing_before>0,"reproduces missing data after new allocation");
 printf("PASS: %d fresh chunk layouts, all argument words retained, logical counts and empty reuse\n",cases);
}
'''
checks=checks.replace('COPY',copy).replace('ALLOCATION',allocation).replace('REUSE',reuse)
with tempfile.TemporaryDirectory(prefix='sparc-fresh-chunk-') as tmp:
 d=Path(tmp);(d/'check.cpp').write_text(model+argsize+checks)
 subprocess.run(['g++','-DSPARC','-std=c++17','-Wall','-Wextra','-Werror',str(d/'check.cpp'),'-o',str(d/'check')],check=True)
 subprocess.run([str(d/'check')],check=True)
