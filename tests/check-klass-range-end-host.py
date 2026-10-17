#!/usr/bin/env python3
"""Compile actual encoding_range_end and compare with wider integer arithmetic."""
from pathlib import Path
import subprocess
import sys
import tempfile
root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
p = root / 'src/hotspot/share/oops/compressedKlass.inline.hpp'
s = p.read_text()
start = s.index('inline address CompressedKlassPointers::encoding_range_end()')
end = s.index('\n}', start) + 2
function = s[start:end]
program = r'''
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
using address = unsigned char*;
#define MIN2(a,b) std::min((a),(b))
static uintptr_t nth_bit(int n) { return uintptr_t(1) << n; }
struct CompressedKlassPointers {
  static address _base;
  static int _shift, bits;
  static int narrow_klass_pointer_bits() { return bits; }
  static address encoding_range_end();
};
address CompressedKlassPointers::_base;
int CompressedKlassPointers::_shift, CompressedKlassPointers::bits;
''' + function + r'''
int main() {
  unsigned cases = 0;
  const uintptr_t max = ~uintptr_t(0);
  const uintptr_t bases[] = {0, 0x10000000ULL, 0x100000000ULL,
      0xfffffff000000000ULL, 0xffffffff10000000ULL, 0xffffffff50000000ULL,
      0xfffffffff0000000ULL, max - 4095};
  for (uintptr_t base : bases) {
    for (int bits : {22, 32}) {
      for (int shift : {0, 3, 6, 10}) {
        CompressedKlassPointers::_base = reinterpret_cast<address>(base);
        CompressedKlassPointers::bits = bits;
        CompressedKlassPointers::_shift = shift;
        uintptr_t got = reinterpret_cast<uintptr_t>(CompressedKlassPointers::encoding_range_end());
        unsigned __int128 wide = (unsigned __int128)base + ((unsigned __int128)1 << (bits + shift));
        uintptr_t want = wide > max ? max : uintptr_t(wide);
        if (got != want || got < base) {
          std::fprintf(stderr, "range wrapped: base=%llx bits=%d shift=%d got=%llx want=%llx\n",
              (unsigned long long)base, bits, shift, (unsigned long long)got, (unsigned long long)want);
          return 1;
        }
        ++cases;
      }
    }
  }
  std::printf("PASS: %u compiled actual-source encoding endpoints, including native failing high range\n", cases);
}
'''
with tempfile.TemporaryDirectory() as td:
    cpp, exe = Path(td)/'test.cpp', Path(td)/'test'
    cpp.write_text(program)
    subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=undefined', str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
# The assertion must use the same overflow-safe endpoint as the public query.
cpp = (root / 'src/hotspot/share/oops/compressedKlass.cpp').read_text()
assert 'const address encoding_end = encoding_range_end();' in cpp
