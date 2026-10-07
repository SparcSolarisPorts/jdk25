// Host model check; does not execute SPARC machine code.
#include <cstdint>
#include <cstring>
#include <cassert>
#include <cstdio>
#include <initializer_list>
using HeapWord = intptr_t;
constexpr intptr_t max_jint=2147483647;
constexpr int STACK_BIAS=2047;
constexpr int freeze_sparc_fp_slot=14;
 int pointer_delta_as_int(intptr_t* a,intptr_t* b){return int(a-b);}
struct Copy { static void conjoint_words(const HeapWord* a, HeapWord* b, size_t n) { memmove(b,a,n*sizeof(HeapWord)); } };
struct frame {
 intptr_t *s,*u,*f; bool heap,interp,empty; int adjustment=0;
 int callee_sp_adjustment() const{return adjustment;}
 void set_sp_adjustment_by_callee(int a){adjustment=a;}
 intptr_t* unextended_sp() const{return u;}
 intptr_t* sp() const {return s;} intptr_t* fp() const {return f;}
 bool is_heap_frame() const{return heap;} bool is_interpreted_frame() const{return interp;}
 bool is_empty() const{return empty;} void set_sp(intptr_t* p){s=p;}
 void set_unextended_sp(intptr_t* p){u=p;}
};
static inline void freeze_sparc_patch_link(const frame& f,
                                            intptr_t* target) {
  if (f.is_heap_frame()) {
    const intptr_t delta = target - f.sp();
    f.sp()[freeze_sparc_fp_slot] = delta > -max_jint && delta < max_jint
        ? delta : (intptr_t)target;
  } else {
    f.sp()[freeze_sparc_fp_slot] = (intptr_t)target - STACK_BIAS;
  }
}

static inline void freeze_sparc_move_caller_window(frame& caller,
                                                  intptr_t* new_sp) {
  if (caller.is_empty() || new_sp == caller.sp()) {
    caller.set_sp(new_sp);
    return;
  }
  const bool interpreted = caller.is_interpreted_frame();
  // Only the architectural L/I save area moves with the window.
  intptr_t* original_sp = interpreted
      ? caller.sp() + caller.callee_sp_adjustment() : caller.unextended_sp();
  Copy::conjoint_words((HeapWord*)caller.sp(), (HeapWord*)new_sp, 16);
  caller.set_sp(new_sp);
  if (interpreted) {
    caller.set_sp_adjustment_by_callee(pointer_delta_as_int(original_sp, new_sp));
    caller.set_unextended_sp(new_sp);
  }
  freeze_sparc_patch_link(caller, caller.fp());
}


int main() {
 size_t cases=0;
 for(bool heap : {false,true}) for(bool interp : {false,true})
 for(int delta=-64;delta<=64;delta++) {
  intptr_t buf[512]; for(int i=0;i<512;i++)buf[i]=10000+i;
  frame f{buf+160,buf+160,buf+400,heap,interp,false};
  intptr_t expected[16]; memcpy(expected,f.sp(),sizeof(expected));
  freeze_sparc_move_caller_window(f,buf+160+delta);
  if(delta!=0) expected[14]=heap ? f.fp()-f.sp() : (intptr_t)f.fp()-STACK_BIAS;
  assert(memcmp(f.sp(),expected,sizeof(expected))==0);
  assert(f.u==(interp ? f.sp():buf+160));
  assert((interp ? f.sp()+f.callee_sp_adjustment():f.unextended_sp())==buf+160);
  // A child frame copy crosses the relocated window. Restore the snapshot
  // exactly as the shared freeze/thaw path does, then check all saved regs.
  intptr_t snapshot[16]; memcpy(snapshot,f.sp(),sizeof(snapshot));
  intptr_t source[64]; for(int i=0;i<64;i++)source[i]=90000+i;
  Copy::conjoint_words(source,f.sp()-8,64);
  Copy::conjoint_words(snapshot,f.sp(),16);
  assert(memcmp(f.sp(),expected,sizeof(expected))==0);
  cases++;
 }
 printf("PASS: %zu heap/native, interpreter/compiled, overlapping-window cases\n",cases);
}
