// Host model check; does not execute SPARC machine code.

#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <array>
#include <vector>
#include <map>
#include <stdexcept>
using address=unsigned char*;
using ByteSize=int;
#define byte_offset_of(t, f) int(offsetof(t,f))
#include "src/hotspot/cpu/sparc/continuationEntry_sparc.hpp"
constexpr intptr_t max_jint=2147483647;
constexpr int STACK_BIAS=2047, wordSize=8;
constexpr int stack_chunk_sparc_i5_slot=13,stack_chunk_sparc_i7_slot=15;
struct frame {static constexpr int pc_return_offset=8;intptr_t* locals; intptr_t* interpreter_frame_local_at(int)const{return locals;}};
struct Stream {
 intptr_t *_sp,*_end,*_unextended_sp,*_pd_younger_sp=nullptr; address _pd_pc;
 std::map<address,bool> interpreted_pc; std::map<intptr_t*,intptr_t*> locals;
 bool is_interpreted()const{return interpreted_pc.count(_pd_pc)!=0;}
 intptr_t* fp()const{return _sp+_sp[14];}
 frame to_frame(){return {locals.at(_sp)};}
 void next(){
  const bool interpreted = is_interpreted();
  intptr_t* sender_sp = fp();
  intptr_t* sender_unextended_sp = sender_sp;
  if (interpreted) {
    // Saved I5 is relative to FP in a chunk and records the sender's
    // original SP before an interpreted callee extended its window.
    intptr_t raw = _sp[stack_chunk_sparc_i5_slot];
    sender_unextended_sp = raw > -max_jint && raw < max_jint
        ? sender_sp + raw : (intptr_t*)raw;
  }
  const bool bottom = sender_sp >= _end ||
      (interpreted && to_frame().interpreter_frame_local_at(0) + 1 >= _end);
  _pd_pc = (address)_sp[stack_chunk_sparc_i7_slot] + frame::pc_return_offset;
  _pd_younger_sp = _sp;
  _sp = bottom ? _end : sender_sp;
  _unextended_sp = bottom ? _end : (is_interpreted() ? _sp : sender_unextended_sp);
 }
};
enum Reg {G1,G2_thread,G3_scratch,G4_scratch,G5,SP,L0=16,I0=24};
int as_lRegister(int i){return L0+i;} int as_iRegister(int i){return I0+i;}
int in_bytes(int x){return x;}
struct ContinuationEntry {static int thaw_bottom_offset(){return ContinuationEntryPD::thaw_bottom_offset();}};
struct Assembler {enum {equal,pt};};
struct Label {int pos=-1;};
struct Inst{int op,a,b,c;Label* label;};
struct Macro {
 std::vector<Inst> code;
 void ld_ptr(int a,int b,int c){code.push_back({0,a,b,c,nullptr});}
 void sub(int a,int b,int c){code.push_back({1,a,b,c,nullptr});}
 void add(int a,int b,int c){code.push_back({2,a,b,c,nullptr});}
 void mov(int a,int b){code.push_back({3,a,b,0,nullptr});}
 void cmp_and_brx_short(int a,int b,int,int,Label& l){code.push_back({4,a,b,0,&l});}
 void ba(Label& l){code.push_back({5,0,0,0,&l});}
 Macro* delayed(){return this;} void nop(){}
 void save(int a,int b,int c){code.push_back({6,a,b,c,nullptr});}
 void bind(Label& l){l.pos=code.size();}
 // Labels must remain alive while executing the emitted sequence.
 void execute(int depth,std::array<intptr_t,32>& r,const std::map<intptr_t,intptr_t>& mem,const std::vector<intptr_t>& chain){
  int count=0,saves=0;
  for(size_t pc=0;pc<code.size();){
   if(++count>1000000)throw std::runtime_error("window walk failed to terminate");
   auto x=code[pc++];
   switch(x.op){
   case 0:r[x.c]=mem.at(r[x.a]+x.b);break;
   case 1:r[x.c]=r[x.a]-(x.b==STACK_BIAS ? x.b:r[x.b]);break;
   case 2:r[x.c]=r[x.a]+x.b;break;
   case 3:r[x.b]=r[x.a];break;
   case 4:if(r[x.a]==r[x.b])pc=x.label->pos;break;
   case 5:pc=x.label->pos;break;
   case 6:
    r[x.c]=r[x.a]+r[x.b];
    ++saves;assert(r[SP]+STACK_BIAS==chain[depth-saves]);break;
   }
  }
  assert(saves==depth);
  for(int i=0;i<16;i++)assert(r[L0+i]==mem.at(chain[0]+i*wordSize));
 }
};
void rebuild(int depth,std::array<intptr_t,32>& r,const std::map<intptr_t,intptr_t>& mem,const std::vector<intptr_t>& chain){Macro m;
    // An interpreted bottom frame can extend the entry window below its
    // canonical SP. The slow thaw records that physical boundary explicitly.
    m.ld_ptr(G1, in_bytes(ContinuationEntry::thaw_bottom_offset()), G1);
    m.sub(G1, STACK_BIAS, SP);

    // Find each child using its saved I6. Do not borrow Java spill slots for
    // reverse links: compiled frames may keep live values immediately above
    // the 16-word architectural save area. No safepoint occurs in this loop.
    Label rebuild, find_child, child_found, windows_ready;
    m.bind(rebuild);
    m.add(SP, STACK_BIAS, G3_scratch);
    m.cmp_and_brx_short(G3_scratch, G4_scratch, Assembler::equal,
                         Assembler::pt, windows_ready);
    m.mov(G4_scratch, G1);
    m.bind(find_child);
    m.ld_ptr(G1, 14 * wordSize, G3_scratch);
    m.cmp_and_brx_short(G3_scratch, SP, Assembler::equal,
                         Assembler::pt, child_found);
    m.add(G3_scratch, STACK_BIAS, G1);
    m.ba(find_child);
    m.delayed()->nop();
    m.bind(child_found);
    m.sub(G1, STACK_BIAS, G3_scratch);
    m.sub(G3_scratch, SP, G3_scratch);
    m.save(SP, G3_scratch, SP);
    for (int reg = 0; reg < 8; reg++) {
      m.ld_ptr(SP, STACK_BIAS + reg * wordSize, as_lRegister(reg));
      m.ld_ptr(SP, STACK_BIAS + (8 + reg) * wordSize, as_iRegister(reg));
    }
    m.ba(rebuild);
    m.delayed()->nop();
    m.bind(windows_ready);

 m.execute(depth,r,mem,chain);
}
int main(){
 size_t cases=0;
 for(int depth=1;depth<=40;depth++)for(int extend: {0,16,128,1024}){
  std::map<intptr_t,intptr_t> mem;std::vector<intptr_t> chain;
  intptr_t pos=0x100000;
  for(int i=0;i<=depth;i++){chain.push_back(pos);pos+=8*(18+(i%7)*2);}
  const intptr_t entry=chain.back()+extend;
  mem[entry+ContinuationEntry::thaw_bottom_offset()]=chain.back();
  for(int i=0;i<depth;i++){
   for(int j=0;j<18;j++)mem[chain[i]+j*8]=0x1000+i*100+j;
   mem[chain[i]+14*8]=chain[i+1]-STACK_BIAS;
  }
  const auto before=mem;
  std::array<intptr_t,32> r{};r[G1]=entry;r[G4_scratch]=chain[0];
  rebuild(depth,r,mem,chain);
  assert(mem==before); // both live spill words 16/17 and all metadata intact
  ++cases;
 }
 intptr_t buf[256]{};
 address c1=(address)uintptr_t(0x10008),c2=(address)uintptr_t(0x20008),ip=(address)uintptr_t(0x30008);
 for(bool interpreted: {false,true})for(int gap: {18,20,32,64}){
  buf[14]=gap;buf[15]=(intptr_t)c2-8;buf[13]=6;
  buf[gap+14]=256-gap;buf[gap+15]=0x40000;
  buf[16]=0xabcdef;buf[17]=0xfedcba;
  Stream st{buf,buf+256,buf,nullptr,interpreted?ip:c1,{},{{buf,buf+gap+8}}};
  if(interpreted)st.interpreted_pc[ip]=true;
  st.next();assert(st._sp==buf+gap);assert(st._pd_pc==c2);
  assert(st._pd_younger_sp==buf);
  assert(st._unextended_sp==buf+gap+(interpreted?6:0));
  assert(buf[16]==0xabcdef&&buf[17]==0xfedcba);
  st.next();assert(st._sp==buf+256);++cases;
 }
 // An interpreted bottom frame can have FP below end while locals reach end.
 buf[14]=100;buf[13]=0;buf[15]=0;
 Stream bottom{buf,buf+120,buf,nullptr,ip,{{ip,true}},{{buf,buf+119}}};
 bottom.next();assert(bottom._sp==buf+120);++cases;
 printf("PASS: %zu emitted window-rebuild / saved-PC stream cases; live spills intact\n",cases);
}
