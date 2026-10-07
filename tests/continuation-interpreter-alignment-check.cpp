
#include <cassert>
#include <cstdint>
#include <algorithm>
#include <cstdio>
using HeapWord=intptr_t;
#undef assert
#define assert(x, ...) ((x)?(void)0:__builtin_trap())
namespace frame { constexpr int frame_alignment=16, register_save_words=16; }
intptr_t* align_down(intptr_t* p,int n) {return (intptr_t*)((uintptr_t)p & ~(uintptr_t)(n-1));}
bool is_aligned(intptr_t* p,int n){return (uintptr_t)p%n==0;}
struct FKind {static constexpr bool interpreted=true;};
struct Frame {intptr_t* spv; intptr_t* fpv; intptr_t* sp()const{return spv;} intptr_t* unextended_sp()const{return spv;} intptr_t* fp()const{return fpv;} bool is_interpreted_frame()const{return true;} int compiled_frame_stack_argsize()const{return 0;} void set_sp(intptr_t*){} };
intptr_t* align(const Frame&,intptr_t* p,Frame&,bool){return p;}
void copy_from_chunk(intptr_t* a,intptr_t*b,int n){std::copy(a,a+n,b);}
int main(){int cases=0;
for(int delta=24;delta<=81;delta++) for(int size=delta+16;size<=delta+35;size++) {
 alignas(16) intptr_t heap[256],native[512]; std::fill_n(native,512,-1);
 for(int i=0;i<256;i++)heap[i]=0x1000+i;
 Frame hf{heap,heap+delta},caller{native+400,native+432};
 int fsize=size; bool bottom=true;
  const int interpreter_padding = FKind::interpreted
      ? ((hf.fp() - hf.unextended_sp()) & 1) : 0;
  intptr_t* frame_sp = caller.unextended_sp() - fsize - interpreter_padding;
  if (FKind::interpreted) {
    frame_sp = align_down(frame_sp, frame::frame_alignment);
  }

  if (!FKind::interpreted &&
      (bottom || caller.is_interpreted_frame())) {
    const int argsize = hf.compiled_frame_stack_argsize();
    frame_sp -= argsize;
    caller.set_sp(caller.sp() - argsize);
    frame_sp = align(hf, frame_sp, caller, bottom);
  }

  intptr_t* frame_fp = frame_sp + (hf.fp() - hf.unextended_sp())
      + interpreter_padding;
  assert(is_aligned(frame_fp, frame::frame_alignment), "native sender window alignment");

 intptr_t* heap_frame_top=heap; intptr_t*stack_frame_top=frame_sp;
  assert(fsize >= frame::register_save_words, "complete interpreter window");
  copy_from_chunk(heap_frame_top, stack_frame_top, frame::register_save_words);
  if (interpreter_padding != 0) stack_frame_top[frame::register_save_words] = 0;
  copy_from_chunk(heap_frame_top + frame::register_save_words,
                  stack_frame_top + frame::register_save_words + interpreter_padding,
                  fsize - frame::register_save_words);

 assert(is_aligned(frame_sp,16)&&is_aligned(frame_fp,16));
 assert(caller.sp()-frame_sp-fsize<=2);
 for(int i=0;i<16;i++)assert(frame_sp[i]==heap[i]);
 for(int i=16;i<fsize;i++)assert(frame_sp[i+interpreter_padding]==heap[i]);
 for(int off=-8;off<16;off++)assert(frame_fp[off]==heap[delta+off]);
 assert(frame_sp[-1]==-1); assert(frame_sp[fsize+interpreter_padding]==-1);
 cases++;
}printf("PASS: %d extracted interpreter layout/copy cases\n",cases);}
