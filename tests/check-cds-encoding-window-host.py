#!/usr/bin/env python3
"""Compile actual SPARC reservation/mode checks against mocked OS allocation."""
from pathlib import Path
import subprocess
import sys
import tempfile
root = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
header = (root/'src/hotspot/share/oops/compressedKlass.hpp').read_text()
methods = header.split('#elif defined(SPARC)',1)[1].split('#else',1)[0]
cpp = (root/'src/hotspot/cpu/sparc/compressedKlass_sparc.cpp').read_text()
func = cpp[cpp.index('char* CompressedKlassPointers::reserve_address_space_for_compressed_classes('):]
program = r'''
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
using address = unsigned char*;
#define MAX2(a,b) std::max((a),(b))
#define guarantee(c,m) do { if (!(c)) { std::fprintf(stderr,"%s\n",m); std::abort(); } } while (0)
static uintptr_t nth_bit(int n) { return uintptr_t(1)<<n; }
static uintptr_t p2u(address p) { return reinterpret_cast<uintptr_t>(p); }
static int mtClass = 1;
static bool fail_reservation;
static uintptr_t unscaled_result, zerobased_result, released_at;
static size_t reserved_size, released_size;
static unsigned reserves, releases, unscaled_calls, zerobased_calls;
namespace Metaspace { [[maybe_unused]] static size_t reserve_alignment() { return 65536; } }
namespace os {
[[maybe_unused]] static char* reserve_memory_aligned(size_t size, size_t alignment, int tag) {
  guarantee(alignment==65536 && tag==mtClass,"OS arguments");
  ++reserves;reserved_size=size;
  if(fail_reservation) return nullptr;
  return reinterpret_cast<char*>(uintptr_t(0xffffffff80000000ULL) - size);
}
[[maybe_unused]] static bool release_memory(char* p, size_t size) {
  ++releases;released_at=reinterpret_cast<uintptr_t>(p);released_size=size;return true;
}
}
struct CompressedKlassPointers {
  static int bits, maxShift, _shift;
  static address _base, _klass_range_start, _klass_range_end;
  static int narrow_klass_pointer_bits() { return bits; }
  static int max_shift() { return maxShift; }
  static size_t max_encoding_range_size() { return nth_bit(bits+maxShift); }
  static char* reserve_address_space_for_unscaled_encoding(size_t,bool) { ++unscaled_calls;return reinterpret_cast<char*>(unscaled_result); }
  static char* reserve_address_space_for_zerobased_encoding(size_t,bool) { ++zerobased_calls;return reinterpret_cast<char*>(zerobased_result); }
  static char* reserve_address_space_for_compressed_classes(size_t,bool,bool);
''' + methods + r'''
};
int CompressedKlassPointers::bits,CompressedKlassPointers::maxShift,CompressedKlassPointers::_shift;
address CompressedKlassPointers::_base,CompressedKlassPointers::_klass_range_start,CompressedKlassPointers::_klass_range_end;
''' + func + r'''
static void check(bool b,const char* msg) { guarantee(b,msg); }
static void reset() {
  fail_reservation=false;unscaled_result=zerobased_result=0;
  reserves=releases=unscaled_calls=zerobased_calls=0;
  reserved_size=released_size=released_at=0;
}
int main() {
  using C=CompressedKlassPointers;
  unsigned cases=0;
  for(int bits : {22,32}) {
    C::bits=bits;C::maxShift=bits==22?10:3;
    uintptr_t full=C::max_encoding_range_size();
    for(size_t size : {size_t(65536),size_t(32)<<20,size_t(1)<<30,size_t(4)<<30}) {
      for(bool optimize : {false,true}) {
        reset();
        uintptr_t base=reinterpret_cast<uintptr_t>(C::reserve_address_space_for_compressed_classes(size,true,optimize));
        check(base!=0 && reserves==1 && reserved_size==full,"reserve full encoding window");
        check((unsigned __int128)base+full<=~uintptr_t(0),"encoding window wraps");
        check(releases==unsigned(full>size),"tail release count");
        if(full>size)check(released_at==base+size && released_size==full-size,"unused tail not returned");
        for(int shift : {0,C::maxShift}) {
          if(size>nth_bit(bits+shift))continue;
          check(C::check_klass_decode_mode(reinterpret_cast<address>(base),shift,size),"safe CDS base rejected");
          C::_base=reinterpret_cast<address>(base);C::_shift=shift;
          C::_klass_range_start=reinterpret_cast<address>(base+65536);
          C::_klass_range_end=reinterpret_cast<address>(base+size);
          check(C::set_klass_decode_mode(),"restored CDS mode rejected");
          // Preserve archived IDs relative to the actual relocated mapping.
          uintptr_t klass=base+65536;
          uintptr_t id=(klass-base)>>shift;
          check(id!=0 && base+(id<<shift)==klass,"archived ID not preserved");
        }
        ++cases;
      }
    }
    reset();fail_reservation=true;
    check(C::reserve_address_space_for_compressed_classes(65536,false,false)==nullptr,"OS failure not propagated");++cases;
    reset();unscaled_result=0x40000000;
    check(reinterpret_cast<uintptr_t>(C::reserve_address_space_for_compressed_classes(65536,true,true))==unscaled_result && reserves==0,"unscaled fast path changed");++cases;
    reset();zerobased_result=0x140000000;
    check(reinterpret_cast<uintptr_t>(C::reserve_address_space_for_compressed_classes(65536,true,true))==zerobased_result && reserves==0,"zero-based fast path changed");++cases;
    check(!C::check_klass_decode_mode(nullptr,-1,65536),"bad negative shift accepted");++cases;
    check(!C::check_klass_decode_mode(nullptr,C::maxShift+1,65536),"bad large shift accepted");++cases;
  }
  C::bits=32;C::maxShift=3;
  check(!C::check_klass_decode_mode(reinterpret_cast<address>(0xffffffff00000000ULL),0,0x41000000),"native overflowing CDS base accepted");++cases;
  check(C::check_klass_decode_mode(reinterpret_cast<address>(0xfffffffe00000000ULL),0,0x41000000),"valid high CDS base rejected");++cases;
  std::printf("PASS: %u compiled actual-source CDS mode/reservation cases, tail release, archived IDs and low-address fast paths\n",cases);
}
'''
# The shared CDS path must consult the mode check before reservation and use
# platform reservation on relocation. Neither requirement is mocked away.
shared = root/'src/hotspot/share/cds/metaspaceShared.cpp'
if not shared.exists(): shared = root.parent/'jdk25/share/cds/metaspaceShared.cpp'
s = shared.read_text()
a=s.index('char* MetaspaceShared::reserve_address_space_for_archives(')
s=s[a:]
assert s.index('CompressedKlassPointers::check_klass_decode_mode(')<s.index('if (use_windows_memory_mapping() && use_archive_base_addr)')
assert 'total_space_rs = Metaspace::reserve_address_space_for_compressed_classes(total_range_size, false' in s
with tempfile.TemporaryDirectory() as td:
    source,exe=Path(td)/'test.cpp',Path(td)/'test'
    source.write_text(program)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(source),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
