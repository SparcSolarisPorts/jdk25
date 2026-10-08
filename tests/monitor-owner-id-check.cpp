
#include <cstdint>
#include <cassert>
#include <cstdio>
#include <initializer_list>
enum Reg{G0,G2_thread,Rscratch,Rmark,Rbox};
int64_t r[5];int64_t owner,box,owner_id;bool zero;
constexpr int OWNER_OFFSET=128;
#define OM_OFFSET_NO_MONITOR_VALUE_TAG(x) OWNER_OFFSET
namespace JavaThread {int monitor_owner_id_offset(){return 32;}}
int in_bytes(int x){return x;}
void add(Reg a,int b,Reg d){r[d]=r[a]+b;}
void ld_ptr(Reg a,int offset,Reg d){assert(a==G2_thread&&offset==32);r[d]=owner_id;}
void cas_ptr(Reg a,Reg expected,Reg desired){assert(r[a]==4096+OWNER_OFFSET);auto old=owner;if(old==r[expected])owner=r[desired];r[desired]=old;}
void andcc(Reg a,Reg b,Reg){zero=(r[a]&r[b])==0;}
void cmp(Reg a,Reg b){zero=r[a]==r[b];}
void st_ptr(Reg a,Reg,int){box=r[a];}
namespace BasicLock {int displaced_header_offset_in_bytes(){return 0;}}
void lock_emitted(){
   add(Rmark, OM_OFFSET_NO_MONITOR_VALUE_TAG(owner), Rmark);
   ld_ptr(G2_thread, in_bytes(JavaThread::monitor_owner_id_offset()), Rscratch);
   cas_ptr(Rmark, G0, Rscratch);
   andcc(Rscratch, Rscratch, G0);             // set ICCs for done: icc.zf iff success
   // set icc.zf : 1=success 0=failure
   // ST box->displaced_header = NonZero.
   // Any non-zero value suffices:
   //    markWord::unused_mark(), G2_thread, RBox, RScratch, rsp, etc.
   st_ptr(Rbox, Rbox, BasicLock::displaced_header_offset_in_bytes());
}
void reacquire_emitted(){
   add(Rmark, OM_OFFSET_NO_MONITOR_VALUE_TAG(owner), Rmark);
   ld_ptr(G2_thread, in_bytes(JavaThread::monitor_owner_id_offset()), Rscratch);
   cas_ptr(Rmark, G0, Rscratch);
   cmp(Rscratch, G0);
}
int main(){int cases=0;
for(auto id:{int64_t(2),int64_t(77),int64_t(0x100000001)}) {
 for(auto initial:{int64_t(0),id,id+1}) {
  r[G0]=0;r[G2_thread]=0x123456780;r[Rmark]=4096;r[Rbox]=8192;
  owner_id=id;owner=initial;lock_emitted();
  assert(zero==(initial==0));assert(owner==(initial==0?id:initial));assert(box==8192);cases++;
  r[Rmark]=4096;owner=initial;reacquire_emitted();
  assert(zero==(initial==0));assert(owner==(initial==0?id:initial));cases++;
 }
}
printf("PASS: %d extracted owner-CAS cases; acquired owners are IDs, not thread pointers\n",cases);
}
