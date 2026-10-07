// Host model check; does not execute SPARC machine code.

#include <cstdint>
#include <cstring>
#include <cassert>
#include <cstdio>
#include <map>
#include <initializer_list>
#define SPARC
using address=unsigned char*;
constexpr int STACK_BIAS=2047,sparc_i5_saved_sp_slot=13;
struct frame {
 intptr_t *s,*u,*p; bool interp; int adjust=0;
 intptr_t* sp()const{return s;} intptr_t* fp()const{return p;}
 intptr_t* unextended_sp()const{return u;}
 bool is_heap_frame()const{return false;}
 bool is_interpreted_frame()const{return interp;}
 int callee_sp_adjustment()const{return adjust;}
 void set_interpreter_frame_sender_sp(intptr_t* x){s[13]=(intptr_t)x-STACK_BIAS;}
};
namespace ContinuationHelper {struct InterpretedFrame {static void patch_sender_sp(frame&,const frame&);};}
inline void ContinuationHelper::InterpretedFrame::patch_sender_sp(
    frame& f, const frame& caller) {
  // I5 restores the caller's SP before this interpreted callee extended it.
  // I6 remains the physical caller window address used while the callee runs.
  intptr_t* sp = caller.is_interpreted_frame()
      ? caller.sp() + caller.callee_sp_adjustment() : caller.unextended_sp();
  f.sp()[sparc_i5_saved_sp_slot] = f.is_heap_frame()
      ? (intptr_t)(sp - f.fp())
      : (intptr_t)sp - STACK_BIAS;
  f.set_interpreter_frame_sender_sp(sp);
}

void patch(frame& f,const frame& caller,bool bottom){
  if (f.is_interpreted_frame()) {
    ContinuationHelper::InterpretedFrame::patch_sender_sp(f, caller);
#ifdef SPARC
    if (bottom) {
      // The entry window was relocated for this interpreter frame's locals.
      // RESTORE(I5, 0, SP) must refill that physical window, not the stale
      // canonical save area. Entry cleanup resets SP after the refill.
      f.set_interpreter_frame_sender_sp(caller.sp());
    }
#endif
  }

}
enum {G1,G2_thread,SP};
struct JavaThread{static int cont_entry_offset(){return 0;}};
int in_bytes(int x){return x;}
struct Macro {
 intptr_t r[3]{};std::map<intptr_t,intptr_t> mem;
 void ld_ptr(int a,int b,int c){r[c]=mem.at(r[a]+b);}
 void sub(int a,int b,int c){r[c]=r[a]-b;}
};
void cleanup_entry(Macro& m){
  m.ld_ptr(G2_thread, in_bytes(JavaThread::cont_entry_offset()), G1);
  m.sub(G1, STACK_BIAS, SP);

}
int main(){
 alignas(16) intptr_t carrier[256],java[32]{};
 int count=0;
 for(int extension: {22,24,32,48})for(bool caller_interp: {false,true}){
  for(int i=0;i<256;i++)carrier[i]=0xdead0000+i;
  intptr_t* canonical=carrier+128;intptr_t* physical=canonical-extension;
  intptr_t expected[16];for(int i=0;i<16;i++)expected[i]=physical[i]=0x1000+i;
  frame caller{physical,canonical,carrier+240,caller_interp,extension};
  frame f{java,java,physical,true};
  patch(f,caller,true);
  intptr_t* refill=(intptr_t*)(java[13]+STACK_BIAS);
  assert(refill==physical);
  assert(memcmp(refill,expected,sizeof(expected))==0);
  assert(memcmp(canonical,expected,sizeof(expected))!=0); // old SP refilled stale data
  Macro m;m.r[G2_thread]=0x100;m.mem[0x100]=(intptr_t)canonical;
  m.r[SP]=(intptr_t)refill-STACK_BIAS;cleanup_entry(m);
  assert(m.r[SP]+STACK_BIAS==(intptr_t)canonical);
  patch(f,caller,false);assert(java[13]+STACK_BIAS==(intptr_t)canonical);
  ++count;
 }
 printf("PASS: %d bottom-interpreter return/refill/cleanup cases; ordinary sender SP unchanged\n",count);
}
