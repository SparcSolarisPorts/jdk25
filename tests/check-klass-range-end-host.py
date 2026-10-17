#!/usr/bin/env python3
"""Compile the actual SPARC base selector and endpoint; test the encoding ABI."""
from pathlib import Path
import subprocess
import sys
import tempfile
root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
header = (root/'src/hotspot/share/oops/compressedKlass.inline.hpp').read_text()
cpp = (root/'src/hotspot/share/oops/compressedKlass.cpp').read_text()

def function(source, signature):
    start = source.index(signature)
    end = source.index('\n}', start) + 2
    return source[start:end]

selector = function(cpp, 'static address sparc_nonwrapping_klass_base(')
endpoint = function(header, 'inline address CompressedKlassPointers::encoding_range_end()')
assert 'const address encoding_end = encoding_range_end();' in cpp
init = cpp[cpp.index('void CompressedKlassPointers::initialize(address addr, size_t len)'):]
assert init.index('_base = sparc_nonwrapping_klass_base(') < init.index('calc_lowest_highest_narrow_klass_id();')
assert cpp.index('initialize_for_given_encoding(') < cpp.index('static address sparc_nonwrapping_klass_base(')
program = r'''
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
using address = unsigned char*;
#define MAX2(a,b) std::max((a),(b))
#define MIN2(a,b) std::min((a),(b))
static uintptr_t nth_bit(int n) { return uintptr_t(1) << n; }
static uintptr_t p2u(address p) { return reinterpret_cast<uintptr_t>(p); }
static uintptr_t align_down(uintptr_t v, uintptr_t a) { return v & ~(a - 1); }
struct CompressedKlassPointers {
  static address _base;
  static int _shift, bits;
  static int narrow_klass_pointer_bits() { return bits; }
  static address encoding_range_end();
};
address CompressedKlassPointers::_base;
int CompressedKlassPointers::_shift, CompressedKlassPointers::bits;
''' + selector + '\n' + endpoint + r'''
static void check(bool good, const char* what) {
  if (!good) { std::fprintf(stderr, "FAIL: %s\n", what); std::exit(1); }
}
int main() {
  unsigned cases = 0, roundtrips = 0;
  const uintptr_t max = ~uintptr_t(0);
  const uintptr_t bases[] = {0, 0x10000000ULL, 0x100000000ULL,
      0xfffffff000000000ULL, 0xffffffff10000000ULL, 0xffffffff50000000ULL,
      0xfffffffff0000000ULL, max - 4095};
  for (uintptr_t original : bases) {
    for (int bits : {22, 32}) {
      for (int shift : {0, 3, 6, 10}) {
        uintptr_t span = nth_bit(bits + shift);
        uintptr_t alignment = nth_bit(std::max(3, shift));
        uintptr_t base = p2u(sparc_nonwrapping_klass_base(reinterpret_cast<address>(original), bits, shift));
        CompressedKlassPointers::_base = reinterpret_cast<address>(base);
        CompressedKlassPointers::bits = bits;
        CompressedKlassPointers::_shift = shift;
        uintptr_t end = p2u(CompressedKlassPointers::encoding_range_end());
        unsigned __int128 wide = (unsigned __int128)base + ((unsigned __int128)1 << (bits + shift));
        check(wide <= max, "full encoding endpoint wraps");
        check(end - base == span, "encoding API must report the entire span");
        check(base <= original, "base moved upward");
        check(base % alignment == 0, "decode alignment changed");
        if ((unsigned __int128)original + span <= max) {
          check(base == original, "ordinary encoding changed");
        }
        uintptr_t available = std::min(span / 4, max - original);
        available = align_down(available, alignment);
        for (uintptr_t offset : {alignment, available / 2, available - alignment}) {
          offset = align_down(offset, alignment);
          uintptr_t klass = original + offset;
          uintptr_t id = (klass - base) >> shift;
          check(klass >= base && klass < end, "actual Klass outside full interval");
          check(id != 0 && id < nth_bit(bits), "narrow Klass ID invalid");
          check(base + (id << shift) == klass, "Klass encode/decode not reversible");
          ++roundtrips;
        }
        ++cases;
      }
    }
  }
  // Exact native comparison: base=0xffffffff10000000, shift=0, 32 bits.
  uintptr_t b = p2u(sparc_nonwrapping_klass_base(reinterpret_cast<address>(0xffffffff10000000ULL), 32, 0));
  check(b == 0xfffffffefffffff8ULL, "unexpected high-address anchor");
  check(b + nth_bit(32) >= 0xffffffff51000000ULL, "native class range not covered");
  std::printf("PASS: %u compiled actual-source full-span geometries; %u Klass roundtrips; native failing comparison\n", cases, roundtrips);
}
'''
with tempfile.TemporaryDirectory() as td:
    source, exe = Path(td)/'test.cpp', Path(td)/'test'
    source.write_text(program)
    subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=undefined', str(source), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
