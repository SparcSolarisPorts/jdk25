
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <initializer_list>
enum Register{G2_thread,SP,FP,G3_scratch,G4_scratch};uint64_t regs[5],activation;bool branch;
constexpr uint64_t STACK_BIAS=2047;int no_reserved_zone_enabling;
namespace JavaThread{int reserved_stack_activation_offset(){return 128;}}
namespace Assembler{enum {lessUnsigned,pt};}
void ld_ptr(Register,int,Register dest){regs[dest]=activation;}
void add(Register src,uint64_t delta,Register dest){regs[dest]=regs[src]+delta;}
void cmp_and_brx_short(Register lhs,Register rhs,int,int,int){branch=regs[lhs]<regs[rhs];}

void compiled_check(){
  ld_ptr(G2_thread, JavaThread::reserved_stack_activation_offset(), G4_scratch);
  // The activation is the unbiased caller boundary.
  add(FP, STACK_BIAS, G3_scratch);
  cmp_and_brx_short(G3_scratch, G4_scratch, Assembler::lessUnsigned, Assembler::pt, no_reserved_zone_enabling);
}
void interpreter_check(){
    ld_ptr(G2_thread, JavaThread::reserved_stack_activation_offset(), G3_scratch);
    // Match the activation caller boundary.
    add(FP, STACK_BIAS, G4_scratch);
    cmp_and_brx_short(G4_scratch, G3_scratch, Assembler::lessUnsigned, Assembler::pt, no_reserved_zone_enabling);
}

int main(){int cases=0;for(uint64_t mark:{uint64_t(0x100100000),uint64_t(0xffffffff73d00000)})for(int64_t delta:{-4096,-2048,-2047,-16,0,16,2048,4096}){
activation=mark;uint64_t physical=mark+delta;
for(auto check:{compiled_check,interpreter_check}){regs[FP]=physical-STACK_BIAS;regs[SP]=physical-STACK_BIAS-8192;check();assert(branch==(physical<mark));cases++;}}
printf("PASS: %d extracted reserved-stack comparisons use unbiased caller boundaries at, below and above activation\n",cases);}
