#!/usr/bin/env python3
"""Compile actual projection validation with safe and corrupt mock nodes."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
stage=root if (root/'src/hotspot').exists() else root.parent/'verify'
s=(stage/'src/hotspot/share/opto/matcher.cpp').read_text()
a=s.index('void Matcher::sparc_verify_projection(');b=s.index('\n#endif',a);fn=s[a:b]
h=(stage/'src/hotspot/share/opto/matcher.hpp').read_text()
assert h.index('sparc_verify_projection(node, _projection_list.size(), "push")') < h.index('_projection_list.push(node)')
g=(stage/'src/hotspot/share/opto/gcm.cpp').read_text()
a=g.index('Node* projection = _matcher.get_projection(i);')
assert g.index('sparc_verify_projection(projection, i, "gcm")',a) < g.index('unmap_node_from_block(projection)',a)
model=r'''
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <cassert>
using uint=unsigned;
#define PTR_FORMAT "%zx"
static uintptr_t p2i(void* p){return reinterpret_cast<uintptr_t>(p);}
#define guarantee(c, ...) do {if(!(c))throw std::runtime_error(#__VA_ARGS__);}while(0)
struct Node {uint _idx;uint req()const{return 1;}uint outcnt()const{return 0;}};
struct Arena {Node* owned;bool contains(void* n){return n==owned;}};
struct Compile {
 Arena arena;uint limit;const char* stub_name(){return "test-stub";}
 Arena* node_arena(){return &arena;}uint unique(){return limit;}int compile_id(){return 3;}
};
static void logger(const char*,...){}
#define log_debug(tag) logger
struct Matcher {
 Compile* C;uint number_of_projections(){return 1;}
 void sparc_verify_projection(Node*,uint,const char*);
};
'''
checks=r'''
int main(){
 Node node{0};Compile c{{&node},400};Matcher m{&c};
 for(uint i: {0u,1u,63u,64u,399u}){
  node._idx=i;m.sparc_verify_projection(&node,0,"push");
  m.sparc_verify_projection(&node,0,"post-match");
  m.sparc_verify_projection(&node,0,"gcm");
 }
 for(Node* p: {static_cast<Node*>(nullptr),reinterpret_cast<Node*>(1)}){
  bool caught=false;try {m.sparc_verify_projection(p,0,"gcm");}catch(const std::runtime_error&){caught=true;}
  assert(caught);
 }
 for(uint i: {400u,0xffffffffu}){
  node._idx=i;bool caught=false;
  try {m.sparc_verify_projection(&node,0,"gcm");}catch(const std::runtime_error&){caught=true;}
  assert(caught);
 }
 puts("PASS: actual projection validation; valid nodes, null/foreign pointers, invalid indices and call ordering");
}
'''
with tempfile.TemporaryDirectory(prefix='sparc-projection-') as tmp:
 d=Path(tmp);(d/'check.cpp').write_text(model+fn+checks)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(d/'check.cpp'),'-o',str(d/'check')],check=True)
 subprocess.run([str(d/'check')],check=True)
