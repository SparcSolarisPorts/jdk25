// Host model check; does not execute SPARC machine code.
#include <initializer_list>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#define assert(c,m) do {if(!(c)) std::abort();}while(0)
#define SPARC_ONLY(x) x
using address=unsigned char*;
constexpr int sparc_i7_slot=15;
struct nmethod {
 address handler=(address)uintptr_t(0x40008);
 bool is_method_handle_return(address)const{return false;}
 address deopt_handler_begin()const{return handler;}
 address deopt_mh_handler_begin()const{return handler;}
 nmethod* as_nmethod_or_null(){return this;}
};
struct frame {
 static constexpr int pc_return_offset=8;
 intptr_t *s,*y; mutable address p; bool heap,empty,deopt; mutable nmethod nm;
 intptr_t* sp()const{return s;} intptr_t* younger_sp()const{return y;}
 intptr_t* younger_sp_or_null()const{return y;}
 address* continuation_pc_address()const{return &p;}
 bool is_heap_frame()const{return heap;} bool is_empty()const{return empty;}
 bool is_deoptimized_frame()const{return deopt;} nmethod* cb()const{return &nm;}
 address pc()const{return p;} address raw_pc()const;
};
namespace ContinuationHelper {struct Frame {
 static address* return_pc_address(const frame& f);
 static address real_pc(const frame& f);
 static void patch_pc(const frame& f,address pc);
};}
address frame::raw_pc() const {
  if (is_deoptimized_frame()) {
    nmethod* nm = cb()->as_nmethod_or_null();
    assert(nm != nullptr, "only nmethod is expected here");
    if (nm->is_method_handle_return(pc()))
      return nm->deopt_mh_handler_begin() - pc_return_offset;
    else
      return nm->deopt_handler_begin() - pc_return_offset;
  } else {
    return (pc() - pc_return_offset);
  }
}

inline address* ContinuationHelper::Frame::return_pc_address(const frame& f) {
  return f.younger_sp_or_null() == nullptr
      ? f.continuation_pc_address()
      : (address*)&f.younger_sp()[sparc_i7_slot];
}

inline address ContinuationHelper::Frame::real_pc(const frame& f) {
  // Always used in assertions. Just strip it.
  return f.younger_sp_or_null() == nullptr
      ? f.raw_pc() + frame::pc_return_offset : *return_pc_address(f) + frame::pc_return_offset;
}

inline void ContinuationHelper::Frame::patch_pc(const frame& f, address pc) {
  // A top frame has no younger window holding O7. Its resume PC lives in
  // the chunk header / entry metadata, not in a Java spill slot or frame::_pc.
  // Keep frame::_pc as the logical original PC for deoptimized oop-map lookup.
  if (f.is_empty() || f.younger_sp_or_null() == nullptr) return;
  *return_pc_address(f) = pc - frame::pc_return_offset;
}


int main(){
 intptr_t slots[32]{}; slots[16]=0xdead; slots[17]=0xbeef;
 address pc=(address)uintptr_t(0x10008);
 int count=0;
 for(bool heap: {false,true})for(bool younger: {false,true})for(bool deopt: {false,true}){
  frame f{slots,younger?slots:nullptr,pc,heap,false,deopt,{}};
  address target=deopt?f.nm.handler:pc;
ContinuationHelper::Frame::patch_pc(f, f.raw_pc() SPARC_ONLY(+ frame::pc_return_offset)); // in case we want to deopt the frame in a full transition, this is checked.
  assert(ContinuationHelper::Frame::real_pc(f)==target,"normalized return PC");
  if(younger)assert(slots[15]==(intptr_t)target-8,"I7 stores call PC");
  assert(slots[16]==0xdead&&slots[17]==0xbeef,"live compiler slots unchanged");
  ++count;
 }
 printf("PASS: %d native/heap, top/sender, normal/deoptimized PC patch cases\n",count);
}
