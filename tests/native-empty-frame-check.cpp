
#include <cstdint>
#include <cassert>
#include <cstdio>
using address=unsigned char*;
#define DEBUG_ONLY(x) x
#define CAST_FROM_FN_PTR(t,p) reinterpret_cast<t>(p)
int sent=0;bool first;
struct frame {
 address _pc;intptr_t *_sp,*_fp,*_younger_sp,*_unextended_sp;
 void *_cb,*_oop_map;enum {unknown};int _deopt_state,_frame_index;
 bool _on_heap;intptr_t _sp_adjustment_by_callee;
 enum unpatchable_t{unpatchable};
frame() {
  _pc = nullptr;
  _sp = nullptr;
  _younger_sp = nullptr;
  _unextended_sp = nullptr;
  _fp = nullptr;
    _cb = nullptr;
  _oop_map = nullptr;
  _deopt_state = unknown;
  _on_heap = false;
  DEBUG_ONLY(_frame_index = -1;)
  _sp_adjustment_by_callee = 0;
}



 frame(intptr_t* sp,unpatchable_t,address):frame(){_sp=sp;}
 frame(intptr_t* sp,intptr_t*,bool):frame(){assert(sp!=nullptr);_sp=sp;}
};
intptr_t area[32];
namespace StubRoutines{struct Sparc{
 static intptr_t* flush(){return area;}
 static auto flush_callers_register_windows_func(){return &flush;}
};}
namespace os {
 bool is_first_C_frame(frame*){return first;}
 frame get_sender_for_C_frame(frame*){sent++;return frame(area+16,frame::unpatchable,nullptr);}
 frame current_frame();
}
frame os::current_frame() {
  intptr_t* sp = StubRoutines::Sparc::flush_callers_register_windows_func()();
  frame myframe(sp, frame::unpatchable,
                CAST_FROM_FN_PTR(address, os::current_frame));
  if (os::is_first_C_frame(&myframe)) {
    // stack is not walkable
    return frame(); // Empty frame; the window constructor dereferences its SP.
  } else {
    return os::get_sender_for_C_frame(&myframe);
  }
}

int main(){
 first=true;frame f=os::current_frame();
 assert(f._sp==nullptr&&f._fp==nullptr&&f._pc==nullptr&&f._cb==nullptr&&f._oop_map==nullptr);
 assert(!f._on_heap&&f._sp_adjustment_by_callee==0&&sent==0);
 first=false;f=os::current_frame();assert(f._sp==area+16&&sent==1);
 puts("PASS: extracted native first-frame path returns initialized empty frame; walkable path follows sender");
}
