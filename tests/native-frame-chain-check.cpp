
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstddef>
constexpr intptr_t STACK_BIAS=2047;constexpr int K=1024;
intptr_t windows[160];
struct RegisterImpl {int sp_offset_in_saved_window(){return 14;}} fp_reg;RegisterImpl* FP=&fp_reg;
bool is_aligned(void* p,size_t a){return reinterpret_cast<uintptr_t>(p)%a==0;}
struct frame;
namespace os {bool is_first_C_frame(frame*);bool is_readable_pointer(void* p){auto n=reinterpret_cast<uintptr_t>(p);return n>=reinterpret_cast<uintptr_t>(windows)&&n<=reinterpret_cast<uintptr_t>(windows+159)&&is_aligned(p,8);}}
bool is_pointer_bad(void* p){return !is_aligned(p,8)||!os::is_readable_pointer(p);}
struct frame {intptr_t *_sp,*_fp;bool heap=false;frame(intptr_t* p):_sp(p),_fp(reinterpret_cast<intptr_t*>(p[14]+STACK_BIAS)){};intptr_t*sp(){return _sp;}intptr_t*fp()const{return _fp;}intptr_t*sender_sp(){return _fp;}bool is_heap_frame()const{return heap;}intptr_t*link()const{return _fp;}intptr_t*link_or_null()const;};
inline intptr_t* frame::link_or_null() const {
  if (is_heap_frame()) {
    return link();
  }
  // os::is_first_C_frame needs the caller's FP.  On SPARC, fp() is
  // already the caller's SP, so link() would simply return fp() again.
  // Read the next saved window, checking it before dereferencing it.
  if (fp() == nullptr) {
    return nullptr;
  }
  intptr_t* slot = reinterpret_cast<intptr_t*>(reinterpret_cast<uintptr_t>(fp())
      + FP->sp_offset_in_saved_window() * sizeof(intptr_t));
  if (!is_aligned(slot, sizeof(intptr_t)) || !os::is_readable_pointer(slot)) {
    return nullptr;
  }
  return reinterpret_cast<intptr_t*>(static_cast<uintptr_t>(*slot) + STACK_BIAS);
}
bool os::is_first_C_frame(frame* fr) {

#ifdef _WINDOWS
  return true; // native stack isn't walkable on windows this way.
#endif
  // Load up sp, fp, sender sp and sender fp, check for reasonable values.
  // Check usp first, because if that's bad the other accessors may fault
  // on some architectures.  Ditto ufp second, etc.

  if (is_pointer_bad(fr->sp())) return true;

  uintptr_t ufp    = (uintptr_t)fr->fp();
  if (is_pointer_bad(fr->fp())) return true;

  uintptr_t old_sp = (uintptr_t)fr->sender_sp();
  if ((uintptr_t)fr->sender_sp() == (uintptr_t)-1 || is_pointer_bad(fr->sender_sp())) return true;

  uintptr_t old_fp = (uintptr_t)fr->link_or_null();
  if (old_fp == 0 || old_fp == (uintptr_t)-1 || old_fp == ufp ||
    is_pointer_bad(fr->link_or_null())) return true;

  // stack grows downwards; if old_fp is below current fp or if the stack
  // frame is too large, either the stack is corrupted or fp is not saved
  // on stack (i.e. on x86, ebp may be used as general register). The stack
  // is not walkable beyond current frame.
  if (old_fp < ufp) return true;
  if (old_fp - ufp > 64 * K) return true;

  return false;
}

int main(){windows[14]=reinterpret_cast<intptr_t>(windows+32)-STACK_BIAS;windows[46]=reinterpret_cast<intptr_t>(windows+64)-STACK_BIAS;windows[78]=reinterpret_cast<intptr_t>(windows+96)-STACK_BIAS;windows[110]=-STACK_BIAS;
frame f(windows);assert(f.link()==f.fp());assert(f.link_or_null()==windows+64);assert(!os::is_first_C_frame(&f));
frame caller(windows+32);assert(!os::is_first_C_frame(&caller));frame last(windows+64);assert(os::is_first_C_frame(&last));
f._fp=nullptr;assert(f.link_or_null()==nullptr);f._fp=reinterpret_cast<intptr_t*>(1);assert(f.link_or_null()==nullptr);f._fp=reinterpret_cast<intptr_t*>(uintptr_t(0x100000));assert(f.link_or_null()==nullptr);
puts("PASS: extracted native caller-FP lookup walks valid windows, stops at root and rejects unreadable slots");}
