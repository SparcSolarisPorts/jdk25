#!/usr/bin/env python3
"""Exercise the actual SPARC bitmap-range start against saved-window roots."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
stage=root if (root/'src/hotspot').exists() else root.parent/'verify'
s=(stage/'src/hotspot/share/runtime/continuationFreezeThaw.cpp').read_text()
a=s.index('  } else if (_cont.tail()->has_bitmap() && added_argsize > 0) {')
b=s.index('    clear_bitmap_bits(start, start + argsize_in_bytes);',a)
block=s[a:b]
line=next(x.strip() for x in block.splitlines() if 'address start = (address)(hf.fp()' in x)
model=r'''
#include <cstdint>
#include <cassert>
#include <cstdio>
using address=unsigned char*;
struct frame {static constexpr int register_save_words=16;intptr_t* p;intptr_t* fp()const{return p;}};
'''
checks=r'''
int main(){
 int cases=0;
 for(int slots=1;slots<=192;slots++){
  alignas(16) intptr_t heap[256];frame hf{heap+32};
  bool bits[512];for(bool& b:bits)b=true;
  START
  int begin=int((start-(address)heap)/4),end=begin+slots;
  for(int i=begin;i<end;i++)bits[i]=false;
  int saved=int(((address)hf.fp()-(address)heap)/4);
  for(int i=saved;i<saved+32;i++)assert(bits[i]);
  for(int i=saved+32;i<saved+32+slots;i++)assert(!bits[i]);
  assert(bits[end]); // neighbouring live data remains rooted
  cases++;
 }
 printf("PASS: actual bitmap start, %d argument-slot counts; caller-window roots preserved\n",cases);
}
'''
with tempfile.TemporaryDirectory(prefix='sparc-args-bitmap-') as tmp:
 d=Path(tmp);(d/'check.cpp').write_text(model+checks.replace('START',line))
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(d/'check.cpp'),'-o',str(d/'check')],check=True)
 subprocess.run([str(d/'check')],check=True)
