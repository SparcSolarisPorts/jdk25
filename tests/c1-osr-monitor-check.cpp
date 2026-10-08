// Extracted SPARC C1 OSR emitter; mock assembler enforces instruction range.
#include <cassert>
#include <cstdint>
#include <vector>
#include <iostream>
using Register = int;
constexpr int BytesPerWord=8, OSR_buf=0, G3_scratch=1, O7=2;
struct Assembler { static bool is_simm13(int x) { return x>=-4096 && x<=4095; } };
struct FrameMap { int address_for_monitor_lock(int i){return 2*i;} int address_for_monitor_object(int i){return 2*i+1;} } fmap;
FrameMap* frame_map(){return &fmap;}
struct Mock {
 int64_t regs[3]{}; std::vector<int64_t> buffer, output;
 explicit Mock(int locals,int locks):buffer(locals+2*locks),output(2*locks) {
  regs[OSR_buf]=0x100000000LL;
  for (size_t i=0;i<buffer.size();i++) buffer[i]=0x200000000LL+i*8;
 }
 void set(int n,Register r){regs[r]=n;}
 void add(Register a,Register b,Register r){regs[r]=regs[a]+regs[b];}
 void ld_ptr(Register b,int off,Register r){assert(Assembler::is_simm13(off)); auto index=(regs[b]+off-0x100000000LL)/8; assert(index>=0 && index<(int64_t)buffer.size());regs[r]=buffer[index];}
 void st_ptr(Register r,int index){output.at(index)=regs[r];}
};
void emit(Mock& masm,int monitor_offset,int number_of_locks) {
    for (int i = 0; i < number_of_locks; i++) {
      int slot_offset = monitor_offset - ((i * 2) * BytesPerWord);
      Register monitor_base = OSR_buf;
      // Both words must fit the signed 13-bit displacement. Large local
      // arrays place the monitor beyond that range; materialize its address
      // without clobbering I0 (the locals still use the OSR buffer).
      if (!Assembler::is_simm13(slot_offset) ||
          !Assembler::is_simm13(slot_offset + BytesPerWord)) {
        masm.set(slot_offset, G3_scratch);
        masm.add(OSR_buf, G3_scratch, G3_scratch);
        monitor_base = G3_scratch;
        slot_offset = 0;
      }
#ifdef ASSERT
      // verify the interpreter's monitor has a non-null object
      {
        Label L;
        masm.ld_ptr(monitor_base, slot_offset + 1*BytesPerWord, O7);
        masm.cmp_and_br_short(O7, G0, Assembler::notEqual, Assembler::pt, L);
        masm.stop("locked object is null");
        masm.bind(L);
      }
#endif // ASSERT
      // Copy the lock field into the compiled activation.
      masm.ld_ptr(monitor_base, slot_offset + 0, O7);
      masm.st_ptr(O7, frame_map()->address_for_monitor_lock(i));
      masm.ld_ptr(monitor_base, slot_offset + 1*BytesPerWord, O7);
      masm.st_ptr(O7, frame_map()->address_for_monitor_object(i));
    }
}
int main(){
 int cases=0;
 for(int locals: {0,1,510,511,512,513,2002,65535}) for(int locks:{1,2,8}) {
  Mock masm(locals,locks); emit(masm,8*locals+16*(locks-1),locks);
  assert(masm.regs[OSR_buf]==0x100000000LL);
  for(int i=0;i<locks;i++) {int slot=locals+2*(locks-1-i); assert(masm.output[2*i]==masm.buffer[slot]);assert(masm.output[2*i+1]==masm.buffer[slot+1]);} cases++;
 }
 // Test exact expressions used in the two edited load/store guards.
 for(int type: {0,1}) for(int offset: {-32768,-4096,-4095,0,4087,4088,4095,4096,16016}) {
  constexpr int T_LONG=1, wordSize=8;
  bool actual=Assembler::is_simm13(offset + ((type == T_LONG) ? wordSize : 0));
  bool expected=offset+(type==T_LONG?8:0)>=-4096 && offset+(type==T_LONG?8:0)<=4095;
  assert(actual==expected);cases++;
 }
 std::cout<<"PASS: "<<cases<<" OSR monitor and displacement cases\n";
}
