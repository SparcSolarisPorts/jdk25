// Host geometry model: canonical payload and physical c2i register windows.
// Does not execute SPARC instructions or validate GC/deoptimization maps.
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
int main() {
  int cases = 0, old_failures = 0;
  for (int extension = 0; extension <= 32; extension += 2) {
    for (int frame_size = 32; frame_size <= 96; frame_size += 2) {
      std::array<uint64_t, 512> native{}, chunk{}, restored{}, old_restored{};
      const int original_sp = 128, physical_sp = original_sp - extension;
      const int heap_sp = 256, heap_physical_sp = heap_sp - extension;
      for (int i=0; i<frame_size; ++i) native[original_sp+i] = 0x100+i;
      for (int i=0; i<16; ++i) native[physical_sp+i] = 0xffffffff00000000ULL+i;
      // Existing payload copy starts at the original SP.
      std::memmove(chunk.data()+heap_sp,native.data()+original_sp,frame_size*8);
      if (extension) {
        std::memmove(chunk.data()+heap_physical_sp,native.data()+physical_sp,16*8);
      }
      // v47's destination was physical_sp, while its source was canonical.
      std::memmove(old_restored.data()+physical_sp,chunk.data()+heap_sp,frame_size*8);
      if (extension) {
        std::memmove(old_restored.data()+physical_sp,chunk.data()+heap_physical_sp,16*8);
      }
      bool old_ok = true;
      for (int i=16;i<frame_size;++i)
        old_ok &= old_restored[original_sp+i]==native[original_sp+i];
      if (!old_ok) ++old_failures;
      if (extension) assert(!old_ok); else assert(old_ok);
      // v48 keeps the canonical payload at canonical SP.
      std::memmove(restored.data()+original_sp,chunk.data()+heap_sp,frame_size*8);
      if (extension) {
        std::memmove(restored.data()+physical_sp,chunk.data()+heap_physical_sp,16*8);
      }
      for (int i=0;i<16;++i) assert(restored[physical_sp+i]==native[physical_sp+i]);
      // Window extension may overlap canonical save slots, never Java payload.
      for (int i=16;i<frame_size;++i) assert(restored[original_sp+i]==native[original_sp+i]);
      ++cases;
    }
  }
  assert(old_failures == 528);
  std::printf("PASS: %d layouts; old displaced destination fails %d extended layouts; canonical payload and physical window restored\n",cases,old_failures);
}
