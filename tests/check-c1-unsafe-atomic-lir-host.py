#!/usr/bin/env python3
"""Compile the actual v84 LIR operation against a recording assembler, execute
its emitted paths, and check the allocator operand contract. No SPARC VM claim."""
from pathlib import Path
import subprocess, tempfile
root = Path(__file__).resolve().parents[1]
if not (root/'src/hotspot/share/c1/c1_LIRGenerator.cpp').exists() and not (root/'verify').exists():
    root = root.parent
source = root / 'verify/src/hotspot/share/c1/c1_LIRGenerator.cpp'
if not source.exists(): source = root / 'src/hotspot/share/c1/c1_LIRGenerator.cpp'
s = source.read_text()
# The recorded assembler cannot detect missing production inline definitions.
# SPARC mov(Register, Register) is defined in macroAssembler.inline.hpp;
# including only its declaration compiles but fails to link libjvm (v84).
assert '#include "asm/macroAssembler.inline.hpp"' in s, 'SPARC assembler inline definitions required'

start = s.index('class LIR_OpSparcUnsafeAccess')
end = s.index('\n};', start) + 3
op = s[start:end]
harness = r'''
#include <cstdint>
#include <vector>
#include <map>
#include <stdexcept>
#include <iostream>
#include <cassert>
using Register=int;
const Register G0=0;
enum BasicType {T_SHORT,T_CHAR,T_INT,T_LONG,T_FLOAT,T_DOUBLE};
int type2aelembytes(BasicType t) {return t==T_SHORT||t==T_CHAR ? 2 : t==T_LONG||t==T_DOUBLE ? 8 : 4;}
struct outputStream {template<class...T> void print(const char*,T...) {}};
struct Opr {int r; Register as_pointer_register(){return r;} void print(outputStream*){}};
using LIR_Opr=Opr*;
struct LIR_OprFact {inline static Opr bad{-1};inline static LIR_Opr illegalOpr=&bad;};
struct LIR_OpVisitState {std::vector<LIR_Opr*> ins,outs,temps;
void do_input(LIR_Opr& r){ins.push_back(&r);} void do_output(LIR_Opr& r){outs.push_back(&r);} void do_temp(LIR_Opr& r){temps.push_back(&r);}};
enum LIR_Code {lir_sparc_unsafe_access};
struct LIR_Assembler;
struct LIR_Op {LIR_Opr _result; LIR_Op(LIR_Code,LIR_Opr r,void*):_result(r){} virtual ~LIR_Op()=default;
virtual void visit(LIR_OpVisitState*)=0; virtual const char* name()const=0; virtual void print_instr(outputStream*)const=0;virtual void emit_code(LIR_Assembler*)=0;};
#define assert_different_registers(a,b,c) assert(a!=b && b!=c && a!=c)
struct Label {inline static int next=0;int id=next++;};
struct Assembler {enum {notZero,always,pn,pt};};
struct Inst {int op,a,b,c;};
struct C1_MacroAssembler {
enum {AND,BR,NOP,ST,LD,SHR,SHL,OR,MOV,SLL,SRA};
std::vector<Inst> code;std::map<int,int> labels;
void andcc(int a,int b,int c){code.push_back({AND,a,b,c});}
void br(int cond,bool,int,Label& l){code.push_back({BR,cond,l.id,0});}
C1_MacroAssembler* delayed(){return this;} void nop(){code.push_back({NOP,0,0,0});} void bind(Label& l){labels[l.id]=code.size();}
void stx(int v,int a,int o){code.push_back({ST,v,a,8|(o<<8)});}void stw(int v,int a,int o){code.push_back({ST,v,a,4|(o<<8)});}void sth(int v,int a,int o){code.push_back({ST,v,a,2|(o<<8)});}void stb(int v,int a,int o){code.push_back({ST,v,a,1|(o<<8)});}
void ldx(int a,int o,int v){code.push_back({LD,v,a,8|(o<<8)});}void ldsw(int a,int o,int v){code.push_back({LD,v,a,4|128|(o<<8)});}void ldsh(int a,int o,int v){code.push_back({LD,v,a,2|128|(o<<8)});}void lduh(int a,int o,int v){code.push_back({LD,v,a,2|(o<<8)});}void ldub(int a,int o,int v){code.push_back({LD,v,a,1|(o<<8)});}
void srlx(int a,int b,int c){code.push_back({SHR,a,b,c});}void sllx(int a,int b,int c){code.push_back({SHL,a,b,c});}void or3(int a,int b,int c){code.push_back({OR,a,b,c});}void mov(int a,int b){code.push_back({MOV,a,b,0});}void sll(int a,int b,int c){code.push_back({SLL,a,b,c});}void sra(int a,int b,int c){code.push_back({SRA,a,b,c});}
void run(uint64_t* r,std::vector<unsigned char>& mem) {
bool cc=false;
for(size_t pc=0;pc<code.size();++pc){auto i=code[pc];
switch(i.op){case AND:cc=(r[i.a]&i.b)!=0;break;
case BR:if(i.a==Assembler::always||cc)pc=labels.at(i.b)-1;break; // delay slots are NOPs
case NOP:break;
case ST:{int n=i.c&127;size_t a=r[i.b]+(i.c>>8);for(int k=0;k<n;++k)mem.at(a+k)=r[i.a]>>((n-1-k)*8);break;}
case LD:{int n=i.c&127;size_t a=r[i.b]+(i.c>>8);uint64_t v=0;for(int k=0;k<n;++k)v=(v<<8)|mem.at(a+k);if(i.c&128){if(n==2)v=int64_t(int16_t(v));else v=int64_t(int32_t(v));}r[i.a]=v;break;}
case SHR:r[i.c]=r[i.a]>>i.b;break;case SHL:r[i.c]=r[i.a]<<i.b;break;case OR:r[i.c]=r[i.a]|r[i.b];break;case MOV:r[i.b]=r[i.a];break;
case SLL:r[i.c]=uint32_t(r[i.a])<<i.b;break;case SRA:r[i.c]=int64_t(int32_t(r[i.a])>>i.b);break;
default:throw std::runtime_error("opcode");}r[0]=0;}}
};
struct LIR_Assembler {C1_MacroAssembler recorder; C1_MacroAssembler* masm(){return &recorder;}};
'''
tests = r'''
int main(){size_t count=0;
for(auto type:{T_SHORT,T_CHAR,T_INT,T_LONG,T_FLOAT,T_DOUBLE})for(bool store:{false,true})
for(int alignment=0;alignment<8;++alignment)for(uint64_t pattern:{0ULL,~0ULL,0x80000000ULL,0x8000ULL,0x8000000000000000ULL,0x123456789abcdef0ULL}) {
Opr a{1},v{2},tmp{3},colored{4};LIR_OpSparcUnsafeAccess op(&a,&v,&tmp,type,store);
LIR_OpVisitState state;op.visit(&state);
assert(state.ins.size()==(store?2:1));assert(state.temps.size()==(store?3:2));assert(state.outs.size()==(store?0:1));
if(!store)*state.outs[0]=&colored; // verify emission uses allocator-rewritten output
LIR_Assembler assembler;op.emit_code(&assembler);
uint64_t r[8]={0, uint64_t(64+alignment),pattern,0xcafebabe,0xdeadbeef,0x1122334455667788ULL,9,10};
std::vector<unsigned char> mem(256,0xa5);int n=type2aelembytes(type);
if(!store)for(int k=0;k<n;++k)mem[64+alignment+k]=pattern>>((n-1-k)*8);
auto before=mem;assembler.recorder.run(r,mem);
assert(r[1]==uint64_t(64+alignment));assert(r[5]==0x1122334455667788ULL);
if(store){for(int k=0;k<256;++k){auto expected=k>=64+alignment&&k<64+alignment+n ? (unsigned char)(pattern>>((n-1-(k-64-alignment))*8)) : before[k];assert(mem[k]==expected);}assert(r[2]==pattern);}
else {uint64_t expected=pattern;if(n==2)expected=type==T_CHAR?uint16_t(pattern):uint64_t(int64_t(int16_t(pattern)));else if(n==4)expected=int64_t(int32_t(pattern));assert(r[4]==expected);assert(mem==before);assert(r[2]==pattern);}
++count;
}
std::cout<<"PASS: "<<count<<" actual emitter load/store, alignment, signed/bit-pattern and allocator-coloring cases\n";
}
'''
# Guard against reintroducing allocator-visible branches in either fallback.
for name in ('do_UnsafeGet','do_UnsafePut'):
    body=s[s.index('void LIRGenerator::'+name+'('):]
    body=body[:body.index('\nvoid LIRGenerator::',1)]
    assert 'new LIR_OpSparcUnsafeAccess' in body
    assert 'LabelObj* slow' not in body
with tempfile.TemporaryDirectory() as d:
    cpp=Path(d)/'test.cpp';cpp.write_text(harness+op+tests)
    exe=Path(d)/'test'
    subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
