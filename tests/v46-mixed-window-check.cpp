// Host geometry model: canonical payload and physical c2i register windows.
// Does not execute SPARC instructions or validate GC/deoptimization maps.
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
int main() {
  int cases = 0;
  for (int extension = 0; extension <= 32; extension += 2) {
    for (int frame_size = 32; frame_size <= 96; frame_size += 2) {
      std::array<uint64_t, 512> native{}, chunk{}, restored{};
      const int original_sp = 128, physical_sp = original_sp - extension;
      const int heap_sp = 256, heap_physical_sp = heap_sp - extension;
      for (int i=0; i<frame_size; ++i) native[original_sp+i] = 0x100+i;
      for (int i=0; i<16; ++i) native[physical_sp+i] = 0xffffffff00000000ULL+i;
      // Existing payload copy starts at the original SP.
      std::memmove(chunk.data()+heap_sp,native.data()+original_sp,frame_size*8);
      if (extension) {
        std::memmove(chunk.data()+heap_physical_sp,native.data()+physical_sp,16*8);
      }
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
  std::printf("PASS: %d c2i extensions preserve live L/I windows and payloads\n",cases);
}
