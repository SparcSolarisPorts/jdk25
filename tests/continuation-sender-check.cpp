
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <initializer_list>
#undef assert
#define assert(x, ...) do { if(!(x)) __builtin_abort(); } while(0)
using address=unsigned char*;
struct RegisterMap;struct frame;struct Chunk;
int window_shifts=0,heap_senders=0,top_calls=0,bottom_calls=0,constructed=0,watermarks=0,oop_updates=0;
struct CodeBlob {bool maps=false;bool caller_must_gc_arguments(void*){return false;}void*oop_maps(){return maps?this:nullptr;}} blob;
namespace CodeCache {CodeBlob* find_blob(address){return nullptr;}}
struct RegisterMap {bool heap=false,walk=false,process=false,update=false;Chunk*chunk;intptr_t*window=nullptr;intptr_t*young=nullptr;void*thread(){return this;}bool in_cont(){return heap;}bool walk_cont(){return walk;}bool process_frames(){return process;}bool update_map(){return update;}Chunk*stack_chunk(){return chunk;}void set_include_argument_oops(bool){}void make_integer_regs_unsaved(){}void shift_window(intptr_t*s,intptr_t*y){window=s;young=y;window_shifts++;}};
intptr_t windows[64];
struct frame {
 intptr_t *_sp=windows,*_fp=windows+16,*_young=nullptr;address _pc=nullptr;CodeBlob*_cb=nullptr;bool interpreted=false,entry=false,upcall=false;address next_pc=nullptr;
 frame()=default;frame(intptr_t*s,intptr_t*y,bool):_sp(s),_young(y){assert(s);constructed++;}
 intptr_t*sp()const{return _sp;}intptr_t*sender_sp()const{return _fp;}address sender_pc()const{return next_pc;}
 bool is_entry_frame()const{return entry;}bool is_upcall_stub_frame()const{return upcall;}bool is_interpreted_frame()const{return interpreted;}
 void set_younger_sp(intptr_t*p){_young=p;}
 frame sender_for_entry_frame(RegisterMap*)const{frame f;f._sp=windows+32;return f;}
 frame sender_for_upcall_stub_frame(RegisterMap*)const{frame f;f._sp=windows+48;return f;}
 frame sender_raw(RegisterMap*)const;frame sender(RegisterMap*)const;
};
struct Chunk {bool leave=false;frame sender(const frame&,RegisterMap*m){heap_senders++;m->heap=!leave;frame f;f._sp=windows+8;return f;}};
namespace OopMapSet {void update_register_map(const frame*,RegisterMap*){oop_updates++;}}
namespace Continuation {bool is_return_barrier_entry(address p){return p==reinterpret_cast<address>(999);}frame top_frame(const frame&,RegisterMap*m){top_calls++;m->heap=true;frame f;f._sp=windows+8;return f;}frame continuation_bottom_sender(void*,const frame&,intptr_t*){bottom_calls++;frame f;f._sp=windows+32;return f;}}
namespace StackWatermarkSet {void on_iteration(void*,const frame&){watermarks++;}}
inline frame frame::sender_raw(RegisterMap* map) const {
  assert(map != nullptr, "map must be set");

  // Default is not to follow arguments; update it accordingly below
  map->set_include_argument_oops(false);

  if (map->in_cont()) {
    return map->stack_chunk()->sender(*this, map);
  }

  assert(CodeCache::find_blob(_pc) == _cb, "inconsistent");

  if (is_entry_frame())       return sender_for_entry_frame(map);
  if (is_upcall_stub_frame()) return sender_for_upcall_stub_frame(map);

  intptr_t* younger_sp = sp();
  intptr_t* sp         = sender_sp();

  // Note:  The version of this operation on any platform with callee-save
  //        registers must update the register map (if not null).
  //        In order to do this correctly, the various subtypes of
  //        of frame (interpreted, compiled, glue, native),
  //        must be distinguished.  There is no need on SPARC for
  //        such distinctions, because all callee-save registers are
  //        preserved for all frames via SPARC-specific mechanisms.
  //
  //        *** HOWEVER, *** if and when we make any floating-point
  //        registers callee-saved, then we will have to copy over
  //        the RegisterMap update logic from the Intel code.

  // The constructor of the sender must know whether this frame is interpreted so it can set the
  // sender's _sp_adjustment_by_callee field.  An osr adapter frame was originally
  // interpreted but its pc is in the code cache (for c1 -> osr_frame_return_id stub), so it must be
  // explicitly recognized.

  bool frame_is_interpreted = is_interpreted_frame();
  if (frame_is_interpreted) {
    map->make_integer_regs_unsaved();
    map->shift_window(sp, younger_sp);
  } else if (_cb != nullptr) {
    // Update the locations of implicitly saved registers to be their
    // addresses in the register save area.
    // For %o registers, the addresses of %i registers in the next younger
    // frame are used.
    map->shift_window(sp, younger_sp);
    if (map->update_map()) {
      // Tell GC to use argument oopmaps for some runtime stubs that need it.
      // For C1, the runtime stub might not have oop maps, so set this flag
      // outside of update_register_map.
      map->set_include_argument_oops(_cb->caller_must_gc_arguments(map->thread()));
      if (_cb->oop_maps() != nullptr) {
        OopMapSet::update_register_map(this, map);
      }
    }
  }
  // A partial thaw installs a return barrier in the bottom Java frame.
  // It is a synthetic return PC, not a frame whose saved window can be
  // traversed. Follow the chunk or recover the real continuation entry.
  if (Continuation::is_return_barrier_entry(sender_pc())) {
    if (map->walk_cont()) {
      return Continuation::top_frame(*this, map);
    }
    frame entry = Continuation::continuation_bottom_sender(map->thread(), *this, sp);
    entry.set_younger_sp(younger_sp);
    map->shift_window(entry.sp(), younger_sp);
    return entry;
  }
  return frame(sp, younger_sp, frame_is_interpreted);
}
inline frame frame::sender(RegisterMap* map) const {
  frame result = sender_raw(map);
  if (map->process_frames() && !map->in_cont()) {
    StackWatermarkSet::on_iteration(map->thread(), result);
  }
  return result;
}

int main(){int cases=0;
for(bool process:{false,true}) {
 frame f;RegisterMap map;Chunk chunk;map.chunk=&chunk;map.process=process;
 int before=watermarks;auto result=f.sender(&map);assert(result._sp==windows+16&&constructed==((cases/7)+1));assert(watermarks-before==int(process));cases++;
 f.next_pc=reinterpret_cast<address>(999);before=constructed;result=f.sender(&map);assert(result._sp==windows+32&&result._young==windows);assert(map.window==windows+32&&map.young==windows);assert(constructed==before);cases++;
 map.walk=true;before=watermarks;result=f.sender(&map);assert(map.heap&&result._sp==windows+8&&watermarks==before);cases++;
 result=f.sender(&map);assert(result._sp==windows+8&&map.heap);cases++;
 chunk.leave=true;before=watermarks;result=f.sender(&map);assert(!map.heap&&watermarks-before==int(process));cases++;
 map.walk=false;f.next_pc=nullptr;f.entry=true;result=f.sender(&map);assert(result._sp==windows+32);cases++;
 f.entry=false;f.upcall=true;result=f.sender(&map);assert(result._sp==windows+48);cases++;
}
assert(top_calls==2&&bottom_calls==2&&heap_senders==4);
printf("PASS: %d extracted sender dispatch cases: native, entry, upcall, barriers, chunk entry/exit and watermark hooks\n",cases);
}
