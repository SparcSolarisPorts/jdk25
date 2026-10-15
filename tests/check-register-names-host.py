#!/usr/bin/env python3
"""Compile the actual register-name methods; check boundaries and every name."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
stage=root if (root/'src/hotspot').exists() else root.parent/'verify'
s=(stage/'src/hotspot/cpu/sparc/register_sparc.cpp').read_text()
s=s[s.index('const char* Register::name()'):]
model=r'''
#include <cassert>
#include <cstring>
#include <string>
#include <cstdio>
struct Register {
 static constexpr int number_of_registers=32;
 int value; int encoding()const{return value;}
 bool is_valid()const{return value>=0&&value<number_of_registers;}
 const char* name()const;
};
struct FloatRegister {
 static constexpr int number_of_registers=64;
 int value; int encoding()const{return value;}
 bool is_valid()const{return value>=0&&value<number_of_registers;}
 const char* name()const;
};
'''
checks=r'''
int main(){
 for(int i=0;i<32;i++){
  std::string expected=std::string(1,"GOLI"[i/8])+std::to_string(i%8);
  if(i==14)expected="SP";
  if(i==30)expected="FP";
  assert(expected==Register{i}.name());
 }
 for(int i=0;i<64;i++){
  std::string expected="F"+std::to_string(i);
  if(i>31&&(i&1))expected+="?";
  assert(expected==FloatRegister{i}.name());
 }
 assert(!strcmp(Register{-1}.name(),"noreg"));
 assert(!strcmp(FloatRegister{-1}.name(),"noreg"));
 puts("PASS: actual register-name methods, all 32 integer/64 floating registers and invalid sentinels");
}
'''
with tempfile.TemporaryDirectory(prefix='sparc-register-names-') as tmp:
 d=Path(tmp);(d/'check.cpp').write_text(model+s+checks)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(d/'check.cpp'),'-o',str(d/'check')],check=True)
 subprocess.run([str(d/'check')],check=True)
