#!/usr/bin/env python3
"""Exercise the actual Block_Array::grow body with guarded arena allocations.
This is a host logic check, not execution of the SPARC JVM or generated code.
"""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
rel = Path('src/hotspot/share/opto/block.cpp')
source = root / rel
if not source.exists():
    source = root.parent / 'verify' / rel
text = source.read_text()
body = text[text.index('void Block_Array::grow(uint i) {'):text.index('void Block_List::remove(uint i) {')]
prefix = r'''
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <initializer_list>
#include <map>
#include <stdexcept>
#include <vector>
#include <cstdio>
#undef assert
#define assert(ok, ...) do { if (!(ok)) std::abort(); } while (0)
using uint = unsigned int;
constexpr uint max_juint = UINT32_MAX;
#define DEBUG_ONLY(x)
#define guarantee(ok, ...) do { if (!(ok)) throw std::overflow_error("capacity guarantee"); } while (0)
struct Block {};
static std::map<void*, size_t> bounds;
struct Arena {
  std::vector<unsigned char*> allocations;
  ~Arena() {
    for (auto p : allocations) {
      const size_t n = bounds.at(p + 64);
      for (size_t i=0; i<64; ++i) {
        assert(p[i]==0xA5 && p[n+64+i]==0xA5);
      }
      bounds.erase(p+64); std::free(p);
    }
  }
  void* Amalloc(size_t n) {
    assert(n <= 256 * 1024);
    auto p = static_cast<unsigned char*>(std::malloc(n+128)); assert(p);
    std::memset(p, 0xA5, n+128); allocations.push_back(p);
    bounds[p+64]=n; return p+64;
  }
  void* Arealloc(void* old, size_t old_n, size_t new_n) {
    assert(bounds.at(old)==old_n && new_n>old_n);
    void* p=Amalloc(new_n); std::memcpy(p, old, old_n); return p;
  }
};
struct Copy {
  static void zero_to_bytes(void* dest, size_t n) {
    bool valid=false;
    const uintptr_t d=reinterpret_cast<uintptr_t>(dest);
    for (const auto& allocation : bounds) {
      uintptr_t base=reinterpret_cast<uintptr_t>(allocation.first);
      if (d>=base && d-base<=allocation.second && n<=allocation.second-(d-base)) valid=true;
    }
    assert(valid); std::memset(dest, 0, n);
  }
};
uint next_power_of_2(uint i) {
  assert(i < (uint(1)<<31));
  uint capacity=1; while (capacity<=i) capacity*=2; return capacity;
}
struct Block_Array {
  uint _size; Arena* _arena; Block** _blocks;
  Block_Array(Arena* a,uint n):_size(n),_arena(a),_blocks(nullptr) {
    if (n) {
      _blocks=static_cast<Block**>(a->Amalloc(n*sizeof(Block*)));
      std::memset(_blocks,0,n*sizeof(Block*));
    }
  }
  uint Max() const {return _size;}
  void grow(uint i);
};
'''
suffix = r'''
int main() {
  unsigned checks=0;
  for (uint initial : {0u,1u,3u,8u,64u}) {
    Arena arena;
    Block_Array a(&arena,initial);
    std::vector<Block*> expected(8192,nullptr);
    uint seed=0x12345678;
    for (uint round=0; round<80; ++round) {
      seed=seed*1664525u+1013904223u;
      uint i=round==0?0:((round<18)?((1u<<(round/2))+(round%2)):seed%8192);
      const uint old=a._size;
      if (i>=a._size) a.grow(i);
      assert(a._size>i && a._size>=old);
      for (uint j=0; j<a._size; ++j) assert(a._blocks[j]==expected[j]);
      expected[i]=reinterpret_cast<Block*>(uintptr_t(0x1000+i*16));
      a._blocks[i]=expected[i]; ++checks;
    }
  }
#ifdef SPARC
  for (uint i : {0x80000000u,0xffffffffu}) {
    Arena arena; Block_Array a(&arena,64);
    const size_t count=arena.allocations.size();
    bool rejected=false;
    try { a.grow(i); } catch (const std::overflow_error&) {rejected=true;}
    assert(rejected && a._size==64 && arena.allocations.size()==count);
    ++checks;
  }
#endif
  std::printf("PASS: %u actual-source growth checks; contents, zero tail, bounds and overflow\n",checks);
}
'''
with tempfile.TemporaryDirectory(prefix='jdk25-block-array-') as folder:
    cpp = Path(folder)/'check.cpp'
    cpp.write_text(prefix + body + suffix)
    for mode, flags in [('sparc', ['-DSPARC']), ('generic', [])]:
        binary = Path(folder)/mode
        subprocess.run([os.environ.get('CXX','g++'), '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                        *flags, str(cpp), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
