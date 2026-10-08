
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <vector>
#include <map>
#include <initializer_list>
#undef assert
#define assert(x, ...) do { if (!(x)) { fprintf(stderr,"assertion failed: %s:%d: %s\n",__FILE__,__LINE__,#x); __builtin_abort(); } } while (0)
using Register=int;
using address=unsigned char*;
constexpr Register G0=0,G6_heapbase=6;
bool UseCompressedOops=true;
int LogMinObjAlignmentInBytes=3;
namespace CompressedOops {int shift_value;address base_value;int shift(){return shift_value;}address base(){return base_value;}}
namespace Universe {void* heap(){return reinterpret_cast<void*>(1);}}
struct Label {static int next;int id=next++;};int Label::next=0;
struct Assembler {enum {pt,pn};};enum {rc_z,rc_nz};
struct MacroAssembler {
 enum Op {SLLX,SRLX,SUB,ADD,MOV,BPR};struct Inst{Op op;int a,b,d;bool annul=false;};
 std::vector<Inst> ins;std::map<int,int> labels;
 void sllx(Register a,int b,Register d){ins.push_back({SLLX,a,b,d});}
 void srlx(Register a,int b,Register d){ins.push_back({SRLX,a,b,d});}
 void sub(Register a,Register b,Register d){ins.push_back({SUB,a,b,d});}
 void add(Register a,Register b,Register d){ins.push_back({ADD,a,b,d});}
 void mov(Register a,Register d){ins.push_back({MOV,a,0,d});}
 void bpr(int cond,bool annul,int,Register a,Label& l){ins.push_back({BPR,a,cond,l.id,annul});}
 void bind(Label& l){labels[l.id]=ins.size();}
 MacroAssembler* delayed(){return this;}
 void verify_oop(Register){}
 void encode_heap_oop(Register,Register);void encode_heap_oop_not_null(Register);void encode_heap_oop_not_null(Register,Register);
 void decode_heap_oop(Register,Register);void decode_heap_oop_not_null(Register);void decode_heap_oop_not_null(Register,Register);
 void execute(uint64_t* regs){
  auto step=[&](const Inst& i){switch(i.op){case SLLX:regs[i.d]=regs[i.a]<<i.b;break;case SRLX:regs[i.d]=regs[i.a]>>i.b;break;case SUB:regs[i.d]=regs[i.a]-regs[i.b];break;case ADD:regs[i.d]=regs[i.a]+regs[i.b];break;case MOV:regs[i.d]=regs[i.a];break;default:__builtin_abort();}regs[0]=0;};
  for(size_t pc=0;pc<ins.size();){auto i=ins[pc];if(i.op==BPR){bool taken=(regs[i.a]==0)==(i.b==rc_z);assert(pc+1<ins.size());if(!i.annul||taken)step(ins[pc+1]);pc=taken?labels.at(i.d):pc+2;}else {step(i);pc++;}}
 }
};
void MacroAssembler::encode_heap_oop(Register src, Register dst) {
  assert (UseCompressedOops, "must be compressed");
  assert (Universe::heap() != nullptr, "java heap should be initialized");
  assert (CompressedOops::shift() == 0 ||
          CompressedOops::shift() == LogMinObjAlignmentInBytes, "decode alg wrong");
  verify_oop(src);
  if (CompressedOops::base() == nullptr) {
    srlx(src, CompressedOops::shift(), dst);
    return;
  }
  Label done;
  if (src == dst) {
    // optimize for frequent case src == dst
    bpr(rc_nz, true, Assembler::pt, src, done);
    delayed() -> sub(src, G6_heapbase, dst); // annulled if not taken
    bind(done);
    srlx(src, CompressedOops::shift(), dst);
  } else {
    bpr(rc_z, false, Assembler::pn, src, done);
    delayed() -> mov(G0, dst);
    // could be moved before branch, and annulate delay,
    // but may add some unneeded work decoding null
    sub(src, G6_heapbase, dst);
    srlx(dst, CompressedOops::shift(), dst);
    bind(done);
  }
}

void MacroAssembler::encode_heap_oop_not_null(Register r) {
  assert (UseCompressedOops, "must be compressed");
  assert (Universe::heap() != nullptr, "java heap should be initialized");
  assert (CompressedOops::shift() == 0 ||
          CompressedOops::shift() == LogMinObjAlignmentInBytes, "decode alg wrong");
  verify_oop(r);
  if (CompressedOops::base() != nullptr)
    sub(r, G6_heapbase, r);
  srlx(r, CompressedOops::shift(), r);
}

void MacroAssembler::encode_heap_oop_not_null(Register src, Register dst) {
  assert (UseCompressedOops, "must be compressed");
  assert (Universe::heap() != nullptr, "java heap should be initialized");
  assert (CompressedOops::shift() == 0 ||
          CompressedOops::shift() == LogMinObjAlignmentInBytes, "decode alg wrong");
  verify_oop(src);
  if (CompressedOops::base() == nullptr) {
    srlx(src, CompressedOops::shift(), dst);
  } else {
    sub(src, G6_heapbase, dst);
    srlx(dst, CompressedOops::shift(), dst);
  }
}

void  MacroAssembler::decode_heap_oop(Register src, Register dst) {
  assert (UseCompressedOops, "must be compressed");
  assert (Universe::heap() != nullptr, "java heap should be initialized");
  assert (CompressedOops::shift() == 0 ||
          CompressedOops::shift() == LogMinObjAlignmentInBytes, "decode alg wrong");
  sllx(src, CompressedOops::shift(), dst);
  if (CompressedOops::base() != nullptr) {
    Label done;
    bpr(rc_nz, true, Assembler::pt, dst, done);
    delayed() -> add(dst, G6_heapbase, dst); // annulled if not taken
    bind(done);
  }
  verify_oop(dst);
}

void MacroAssembler::decode_heap_oop_not_null(Register r) {
  // Do not add assert code to this unless you change vtableStubs_sparc.cpp
  // pd_code_size_limit.
  // Also do not verify_oop as this is called by verify_oop.
  assert (UseCompressedOops, "must be compressed");
  assert (Universe::heap() != nullptr, "java heap should be initialized");
  assert (CompressedOops::shift() == 0 ||
          CompressedOops::shift() == LogMinObjAlignmentInBytes, "decode alg wrong");
  sllx(r, CompressedOops::shift(), r);
  if (CompressedOops::base() != nullptr)
    add(r, G6_heapbase, r);
}

void  MacroAssembler::decode_heap_oop_not_null(Register src, Register dst) {
  // Do not add assert code to this unless you change vtableStubs_sparc.cpp
  // pd_code_size_limit.
  // Also do not verify_oop as this is called by verify_oop.
  assert (UseCompressedOops, "must be compressed");
  assert (CompressedOops::shift() == 0 ||
          CompressedOops::shift() == LogMinObjAlignmentInBytes, "decode alg wrong");
  sllx(src, CompressedOops::shift(), dst);
  if (CompressedOops::base() != nullptr)
    add(dst, G6_heapbase, dst);
}
int main(){int cases=0;
for(int shift:{0,3,4})for(uint64_t base:{uint64_t(0),uint64_t(0x800000000),uint64_t(0x100008000)}) {
 if(shift==0&&base!=0)continue;
 CompressedOops::shift_value=shift;CompressedOops::base_value=reinterpret_cast<address>(base);LogMinObjAlignmentInBytes=shift==4?4:3;
 for(uint64_t narrow:{uint64_t(0),uint64_t(8),uint64_t(0xc1d01ff8),uint64_t(0xfffffff0)}) {
  uint64_t oop=narrow==0?0:base+(narrow<<shift);
  for(bool same:{false,true})for(int kind=0;kind<6;kind++) {
   bool encode=kind<3,nonnull=kind!=0&&kind!=3;if(nonnull&&narrow==0)continue;
   uint64_t r[8]={};int src=1,dst=same?1:2;r[src]=encode?oop:narrow;r[6]=base;
   MacroAssembler m;switch(kind){case 0:m.encode_heap_oop(src,dst);break;case 1:dst=src;m.encode_heap_oop_not_null(src);break;case 2:m.encode_heap_oop_not_null(src,dst);break;case 3:m.decode_heap_oop(src,dst);break;case 4:dst=src;m.decode_heap_oop_not_null(src);break;case 5:m.decode_heap_oop_not_null(src,dst);break;}
   m.execute(r);assert(r[dst]==(encode?narrow:oop));cases++;
  }
 }
}
printf("PASS: %d extracted compressed-oop emitter cases (unscaled, scaled, null, aliases, nonzero bases)\n",cases);
}
