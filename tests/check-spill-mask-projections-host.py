#!/usr/bin/env python3
"""Compile actual spill-mask matching tail and verify probe suffix isolation."""
from pathlib import Path
import subprocess,tempfile,zipfile
root=Path(__file__).resolve().parents[1]
stage=root if (root/'src/hotspot').exists() else root.parent/'verify'
s=(stage/'src/hotspot/share/opto/matcher.cpp').read_text()
a=s.index('#ifdef SPARC\n  const uint probe_projection_count');b=s.index('\n// Process Mach IR right after',a)
tail=s[a:b]
model=r'''
#include <vector>
#include <cstdio>
#include <cstdlib>
using uint=unsigned;
static void check(bool c){if(!c){puts("FAIL: probe projections leaked or prefix changed");std::exit(17);}}
#define assert(c, ...) check(c)
struct Node {bool live=true;};
struct RegMask {int value=31;};
struct MachNode: Node {RegMask mask;const RegMask& out_RegMask(){return mask;}};
struct Type {bool vector;bool isa_vect()const{return vector;}};
struct Compile {bool fail;bool failing(){return fail;}bool failure_is_artificial(){return fail;}};
struct Matcher {
 Compile* C;std::vector<Node*> list;std::vector<Node*> added;MachNode machine;uint extra;int specialized=0;
 static bool supports_generic_vector_operands;
 uint number_of_projections(){return list.size();}
 Node* pop_projection(){Node* p=list.back();list.pop_back();return p;}
 MachNode* match_tree(Node*){for(uint i=0;i<extra;++i)list.push_back(added[i]);return C->fail?nullptr:&machine;}
 void specialize_mach_node(MachNode*){++specialized;}
 const RegMask* probe(Node*,uint,const Type*);
};
bool Matcher::supports_generic_vector_operands=false;
const RegMask* Matcher::probe(Node* spill,uint ideal_reg,const Type* t){(void)ideal_reg;
'''
checks=r'''
int main(){int cases=0;
 for(uint prefix=0;prefix<=32;++prefix)for(uint extra=0;extra<=5;++extra)
 for(bool fail:{false,true})for(bool vec:{false,true}){
  Compile c{fail};Matcher m{};m.C=&c;m.extra=extra;
  Node live[33],temporary[6],spill;
  for(uint i=0;i<prefix;++i)m.list.push_back(&live[i]);
  for(uint i=0;i<extra;++i)m.added.push_back(&temporary[i]);
  const auto original=m.list;Type type{vec};Matcher::supports_generic_vector_operands=vec;
  const RegMask* mask=m.probe(&spill,0,&type);
  check(fail?mask==nullptr:mask==&m.machine.mask);
  check(m.specialized==(!fail&&vec?1:0));
#ifdef SPARC
  check(m.list==original);
  // Releasing old probe storage cannot leave references in the real list.
  for(uint i=0;i<extra;++i)temporary[i].live=false;
  for(Node* p:m.list)check(p->live);
#else
  check(m.list.size()==prefix+extra);
  for(uint i=0;i<prefix;++i)check(m.list[i]==original[i]);
#endif
  ++cases;
 }
 printf("PASS: %d actual-source probe cases; success/failure, scalar/vector, preserved prefix and old-arena release\n",cases);
}
'''
with tempfile.TemporaryDirectory(prefix='sparc-spill-projections-') as tmp:
 d=Path(tmp)
 def run(tail,flags,expected):
  (d/'check.cpp').write_text(model+tail+checks)
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',*flags,str(d/'check.cpp'),'-o',str(d/'check')],check=True)
  r=subprocess.run([str(d/'check')],capture_output=True,text=True)
  if r.returncode!=expected:raise RuntimeError(r.stdout+r.stderr)
  print(r.stdout.strip() if expected==0 else "EXPECTED: previous implementation leaks probe projections")
 for flags in (['-DSPARC'],[]):run(tail,flags,0)
 # The previous implementation must fail the same SPARC lifetime check.
 # Derive its unchanged tail by removing only the new scoped cleanup blocks.
 start=tail.index('  MachNode* mspill = match_tree(spill);')
 baseline=tail[start:]
 a=baseline.index('\n#ifdef SPARC');b=baseline.index('\n#endif',a)+len('\n#endif')
 baseline=baseline[:a]+baseline[b:]
 run(baseline,['-DSPARC'],17)
 print('PASS: previous matching tail reproduces the leaked-projection regression')
