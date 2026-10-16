#!/usr/bin/env python3
"""Compile actual entry-map setup and JavaThread's mounted-entry root loop."""
from pathlib import Path
import subprocess,tempfile,zipfile
root=Path(__file__).resolve().parents[1]
stage=root if (root/'src/hotspot').exists() else root.parent/'verify'
s=(stage/'src/hotspot/cpu/sparc/sharedRuntime_sparc.cpp').read_text()
def setup(s):
 a=s.index('static OopMap* sparc_continuation_enter_setup(');b=s.index('\n// A normal return',a)
 return s[a:b]
# The generic traversal is the sole owner of these root slots.
thread=(root.parent/'jdk25/share/runtime/javaThread.cpp')
if not thread.exists():
 print('SKIP: host check needs baseline share/runtime/javaThread.cpp next to staging tree')
 raise SystemExit(0)
src=thread.read_text();a=src.index('  ContinuationEntry* entry = _cont_entry;');b=src.index('\n\n  if (LockingMode',a);loop=src[a:b]
model=r'''
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <vector>
#include <map>
using oop=uintptr_t;
static void check(bool c){if(!c){puts("FAIL: duplicated mounted-entry root adjustment");std::exit(17);}}
#define assert(c, ...) check(c)
constexpr int wordSize=8,STACK_BIAS=2047,SP=1,G2_thread=2,G1=3;
static int in_bytes(int x){return x;}
static bool is_aligned(int v,int a){return v%a==0;}
struct frame{static constexpr int memory_parameter_word_sp_offset=22;};
struct OopMap {int frame_size;std::vector<int> roots;OopMap(int n,int):frame_size(n){}void set_oop(int r){roots.push_back(r);}};
struct VMRegImpl{static constexpr int stack_slot_size=4;static int stack2reg(int x){return x;}};
struct ContinuationEntry{
 oop cont=100,chunk=300;ContinuationEntry* prev=nullptr;
 static int size(){return 384;}static int parent_offset(){return 176;}
 static int cont_offset(){return 184;}static int chunk_offset(){return 192;}
 oop* cont_addr(){return &cont;}oop* chunk_addr(){return &chunk;}
 ContinuationEntry* parent(){return prev;}
};
struct Closure {int calls=0;std::map<oop,oop> forward{{100,200},{200,900},{300,400},{400,901}};
 void do_oop(oop* p){++calls;*p=forward.at(*p);}
};
struct JavaThread {ContinuationEntry* _cont_entry;static int cont_entry_offset(){return 1000;}
 void visit(Closure* f){
'''
assembly=r'''
 }
};
struct MacroAssembler{
 template<class... A>void save(A...){}template<class... A>void ld_ptr(A...){}
 template<class... A>void st_ptr(A...){}template<class... A>void add(A...){}
};
static void fill_continuation_entry(MacroAssembler*){}
#define __ masm->
'''
checks=r'''
int main(){MacroAssembler masm;OopMap* m=sparc_continuation_enter_setup(&masm);
 check(m->frame_size==384/4);
 for(int depth=1;depth<=8;++depth){
  std::vector<ContinuationEntry> entries(depth);
  for(int i=1;i<depth;++i)entries[i].prev=&entries[i-1];
  JavaThread t{&entries.back()};Closure cl;t.visit(&cl);
  // Simulate frame scanning after non-frame thread roots have been adjusted.
  for(auto& e:entries)for(int r:m->roots){
   if(r==ContinuationEntry::cont_offset()/4)cl.do_oop(e.cont_addr());
   if(r==ContinuationEntry::chunk_offset()/4)cl.do_oop(e.chunk_addr());
  }
  for(auto& e:entries)check(e.cont==200 && e.chunk==400);
  check(cl.calls==depth*2);
 }
 delete m;puts("PASS: actual entry OopMap and JavaThread root loop; eight nesting depths, one adjustment per slot");
}
'''
with tempfile.TemporaryDirectory(prefix='sparc-entry-roots-') as tmp:
 d=Path(tmp)
 def run(fn,expected):
  (d/'check.cpp').write_text(model+loop+assembly+fn+checks)
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(d/'check.cpp'),'-o',str(d/'check')],check=True)
  r=subprocess.run([str(d/'check')],capture_output=True,text=True)
  if r.returncode!=expected:raise RuntimeError(r.stdout+r.stderr)
  print(r.stdout.strip() if expected==0 else 'EXPECTED: previous entry OopMap adjusts the same slots twice')
 run(setup(s),0)
 prior=root.parent/'jdk25-sparc-continuations-v76.zip'
 if prior.exists():
  old=zipfile.ZipFile(prior).read('src/hotspot/cpu/sparc/sharedRuntime_sparc.cpp').decode()
  run(setup(old),17)
