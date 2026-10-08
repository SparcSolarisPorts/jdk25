// Extracted fast_aldc null-sentinel emitter with a native-root barrier model.
#include <cassert>
#include <cstdint>
#include <iostream>
using Register=int;using address=unsigned char*;
constexpr Register G3_scratch=0,Lscratch=1,Otos_i=2;
struct Label {};
struct Assembler {enum {notEqual,pt};};
uintptr_t sentinel_slot,handle_storage;
namespace Universe {address the_null_sentinel_addr(){return reinterpret_cast<address>(&handle_storage);}}
struct ExternalAddress {uintptr_t value;explicit ExternalAddress(address p):value(reinterpret_cast<uintptr_t>(p)){}};
struct Mock {
 uintptr_t regs[3]{};bool neq=false,jumped=false;int barriers=0;
 void set(ExternalAddress a,Register r){regs[r]=a.value;}
 void ld_ptr(Register a,int offset,Register r){assert(offset==0);regs[r]=*reinterpret_cast<uintptr_t*>(regs[a]);}
 void resolve_oop_handle(Register a,Register tmp){assert(a!=tmp);regs[a]=*reinterpret_cast<uintptr_t*>(regs[a]);barriers++;}
 void cmp(Register a,Register b){neq=regs[a]!=regs[b];}
 void br(int condition,bool,int,Label&){assert(condition==Assembler::notEqual);jumped=neq;}
 Mock* delayed(){return this;}
 void nop(){}
 void clr(Register r){if(!jumped)regs[r]=0;}
 void bind(Label&){jumped=false;}
};
void emit(Mock& masm) {
    Label notNull;
    masm.set(ExternalAddress((address)Universe::the_null_sentinel_addr()), G3_scratch);
    // Universe stores an OopHandle, not an oop. Load its storage slot and
    // resolve that slot with the native-root barrier before comparing.
    masm.ld_ptr(G3_scratch, 0, G3_scratch);
    masm.resolve_oop_handle(G3_scratch, Lscratch);
    masm.cmp(G3_scratch, Otos_i);
    masm.br(Assembler::notEqual, true, Assembler::pt, notNull);
    masm.delayed()->nop();
    masm.clr(Otos_i);  // nullptr object reference
    masm.bind(notNull);
}
int main(){
 int cases=0;
 for(uintptr_t sentinel: {uintptr_t(0x180000000),uintptr_t(0x280000000),uintptr_t(0x380000000)}) {
  sentinel_slot=sentinel;handle_storage=reinterpret_cast<uintptr_t>(&sentinel_slot);
  for(uintptr_t input: {uintptr_t(0),sentinel,uintptr_t(0x190000008)}) {
   Mock masm;masm.regs[Otos_i]=input;emit(masm);
   assert(masm.regs[Otos_i]==(input==sentinel?0:input));
   assert(masm.barriers==1);cases++;
  }
 }
 std::cout<<"PASS: "<<cases<<" null sentinel/VM-null/object cases across relocated sentinel addresses\n";
}
