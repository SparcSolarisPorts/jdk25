
#include <cstdint>
#include <cstdio>
#include <cassert>
constexpr int max_jint=0x7fffffff, STACK_BIAS=2047;
namespace frame {constexpr int register_save_words=16;}
struct Frame {
 intptr_t *spv,*fpv,*bottom;bool interp;
 intptr_t* sp()const{return spv;} intptr_t* fp()const{return fpv;}
 intptr_t* unextended_sp()const{return spv;}
 bool is_interpreted_frame()const{return interp;}
};
namespace ContinuationHelper {struct InterpretedFrame{
 static intptr_t* frame_bottom(const Frame& f){return f.bottom;}
};}
#include <initializer_list>
static inline intptr_t* freeze_sparc_translate_pointer(
    const Frame& from, const Frame& to, intptr_t* value) {
  return to.sp() + (value - from.sp());
}

static inline void freeze_sparc_derelativize_slot(
    const Frame& heap, const Frame& stack, int slot, bool biased) {
  intptr_t raw = heap.sp()[slot];
  intptr_t* heap_value = raw > -max_jint && raw < max_jint
      ? heap.fp() + raw : (intptr_t*)raw;
  intptr_t* bottom = heap.is_interpreted_frame()
      ? ContinuationHelper::InterpretedFrame::frame_bottom(heap) : heap.fp();
  intptr_t* stack_value = heap_value;
  if (heap_value >= heap.unextended_sp() && heap_value < bottom) {
    if (heap.is_interpreted_frame() &&
        heap_value >= heap.unextended_sp() + frame::register_save_words) {
      // Thaw may insert a word above the register-save area to align FP.
      // Payload pointers must follow FP, not the physical SP displacement.
      stack_value = stack.fp() + (heap_value - heap.fp());
    } else {
      stack_value = freeze_sparc_translate_pointer(heap, stack, heap_value);
    }
  }
  stack.sp()[slot] = biased ? (intptr_t)stack_value - STACK_BIAS
                            : (intptr_t)stack_value;
}


int main(){int cases=0;
 for(int delta=24;delta<=81;delta++)for(int size=delta+16;size<=delta+35;size++) {
 alignas(16) intptr_t heap[256]{},native[512]{};
 const int pad=delta&1;
 Frame hf{heap,heap+delta,heap+size,true};
 Frame sf{native,native+delta+pad,native+size+pad,true};
 for(int target=0;target<size;target++)for(bool biased:{false,true}) {
   heap[3]=target-delta;
   freeze_sparc_derelativize_slot(hf,sf,3,biased);
   intptr_t* expected=native+target+(target>=16?pad:0);
   assert(native[3]==(intptr_t)expected-(biased?STACK_BIAS:0));cases++;
 }
 // Absolute out-of-frame pointer is retained.
 heap[3]=(intptr_t)(heap+size+8);
 freeze_sparc_derelativize_slot(hf,sf,3,false);
 assert(native[3]==(intptr_t)(heap+size+8));
 }
 printf("PASS: %d extracted metadata relocation cases, payload/window pointers and bias\n",cases);
}
