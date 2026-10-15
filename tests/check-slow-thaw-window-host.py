#!/usr/bin/env python3
"""Exercise actual SPARC slow-thaw frame placement with a host stack model."""
from pathlib import Path
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
stage = root if (root/'src/hotspot').exists() else root.parent/'verify'
s = (stage/'src/hotspot/cpu/sparc/continuationFreezeThaw_sparc.inline.hpp').read_text()
def function(marker):
    a=s.index(marker); i=s.index('{',a)+1; depth=1
    while depth:
        depth+=(s[i]=='{')-(s[i]=='}'); i+=1
    return s[a:i]
parts=[function('static inline void freeze_sparc_patch_link('),
       function('static inline void freeze_sparc_move_caller_window('),
       function('static inline void thaw_sparc_restore_caller_window('),
       function('inline intptr_t* ThawBase::align('),
       function('template<typename FKind>\nframe ThawBase::new_stack_frame(')]
shared=(stage/'src/hotspot/share/runtime/continuationFreezeThaw.cpp').read_text()
a=shared.index('  frame f = new_stack_frame<ContinuationHelper::CompiledFrame>')
b=shared.index('  patch(f, caller, is_bottom_frame);',a)
compiled=shared[a:b]
assert compiled.index('(HeapWord*)caller_window') < compiled.index('copy_from_chunk(from, to, sz)')
assert compiled.index('thaw_sparc_restore_caller_window(caller_window, caller.sp(), hf.fp(), added_argsize)') > compiled.index('copy_from_chunk(from, to, sz)')
model=r'''
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#define assert(c, ...) do { if (!(c)) std::abort(); } while(0)
using HeapWord=intptr_t;
constexpr int STACK_BIAS=2047,freeze_sparc_fp_slot=14,max_jint=2147483647;
struct VMRegImpl {static constexpr int slots_per_word=2;};
struct SharedRuntime {static int out_preserve_stack_slots(){return 32;}};
int pointer_delta_as_int(intptr_t* a,intptr_t* b){return int(a-b);}
bool is_aligned(intptr_t* p,int n){return uintptr_t(p)%n==0;}
intptr_t* align_down(intptr_t* p,int n){return (intptr_t*)(uintptr_t(p)&~uintptr_t(n-1));}
struct Copy {static void conjoint_words(HeapWord* a,HeapWord* b,int n){memmove(b,a,n*sizeof(*a));}};
struct frame {
 static constexpr int frame_alignment=16,register_save_words=16;
 intptr_t *s,*u,*f; bool interp=false,heap=false; int args=0,adjustment=0;
 frame(intptr_t* a,intptr_t* b,intptr_t* c,int=0,int=0,int=0,bool h=false):s(a),u(b),f(c),heap(h){}
 intptr_t* sp()const{return s;} intptr_t* unextended_sp()const{return u;} intptr_t* fp()const{return f;}
 bool is_interpreted_frame()const{return interp;} bool is_empty()const{return false;} bool is_heap_frame()const{return heap;}
 void set_sp(intptr_t* a){s=a;} void set_unextended_sp(intptr_t* a){u=a;}
 int callee_sp_adjustment()const{return adjustment;} void set_sp_adjustment_by_callee(int a){adjustment=a;}
 int compiled_frame_stack_argsize()const{return args;} int pc()const{return 0;} int cb()const{return 0;} int oop_map()const{return 0;}
 void set_younger_sp(intptr_t*){}
};
struct ThawBase {
 intptr_t* align(const frame&,intptr_t*,frame&,bool);
 template<typename K> frame new_stack_frame(const frame&,frame&,bool);
};
struct Compiled {
 static constexpr bool interpreted=false;
 static bool is_instance(const frame&){return true;}
 static int size(const frame& f){return int(f.fp()-f.unextended_sp());}
 static int stack_argsize(const frame& f){return f.args;}
};
'''
checks=r'''
int main(){
 unsigned count=0;
 for(int args=0;args<=96;args++)for(int parity=0;parity<2;parity++)for(int interpreted=0;interpreted<2;interpreted++){
  alignas(16) intptr_t stack[2048],heap[256];
  for(int i=0;i<2048;i++)stack[i]=0x50000+i;
  frame caller(stack+1024,stack+1024,stack+1536);caller.interp=interpreted;
  frame hf(heap+32-parity*2,heap+32,heap+64);hf.args=args;
  intptr_t expected[16];memcpy(expected,caller.sp(),sizeof expected);
  ThawBase thaw;frame f=thaw.new_stack_frame<Compiled>(hf,caller,true);
  if(caller.sp()!=stack+1024)expected[14]=(intptr_t)caller.fp()-STACK_BIAS;
  assert(is_aligned(f.sp(),16),"aligned frame");
  assert(f.fp()==caller.sp(),"linked physical boundary");
  assert(memcmp(caller.sp(),expected,sizeof expected)==0,"copied original window, not shifted argument area");
  // Exercise the compiled payload overlap and the caller-window restore.
  intptr_t saved[16];Copy::conjoint_words(caller.sp(),saved,16);
  for(int i=0;i<args;i++){caller.sp()[i]=0x90000+i;hf.fp()[16+i]=0xa0000+i;}
  thaw_sparc_restore_caller_window(saved,caller.sp(),hf.fp(),args);
  for(int i=0;i<args;i++)assert(caller.sp()[16+i]==0xa0000+i,"arguments above window");
  assert(memcmp(caller.sp(),expected,sizeof expected)==0,"window survives payload copy");
  count++;
 }
 printf("PASS: actual slow-thaw placement, %u argument/alignment/caller cases\n",count);
}
'''
with tempfile.TemporaryDirectory(prefix='sparc-slow-thaw-') as tmp:
    d=Path(tmp);(d/'check.cpp').write_text(model+'\n'.join(parts)+checks)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(d/'check.cpp'),'-o',str(d/'check')],check=True)
    subprocess.run([str(d/'check')],check=True)
