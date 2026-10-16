// Native compiler/runtime diagnostic, independent of the Java VM.
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <thread>
#include <vector>

static __attribute__((noinline)) unsigned native_clz32(uint32_t value) {
  // Keep every check as a call with a runtime input; do not constant-fold it.
  asm volatile("" : "+r"(value));
  return __builtin_clz(value);
}
static __attribute__((noinline)) unsigned native_clz64(uint64_t value) {
  asm volatile("" : "+r"(value));
  return __builtin_clzll(value);
}
struct Failure {
  bool failed = false;
  unsigned width = 0, expected = 0, actual = 0;
  uint64_t value = 0;
};
static bool test_value(unsigned width, uint64_t value, unsigned expected, Failure& f) {
  unsigned actual = width == 32 ? native_clz32(static_cast<uint32_t>(value))
                                : native_clz64(value);
  if (actual == expected) return true;
  f.failed = true; f.width = width; f.value = value;
  f.expected = expected; f.actual = actual;
  return false;
}
int main() {
  std::atomic<bool> go(false);
  Failure failures[8];
  std::vector<std::thread> workers;
  for (unsigned worker = 0; worker < 8; ++worker) {
    workers.emplace_back([&, worker] {
      while (!go.load(std::memory_order_acquire)) std::this_thread::yield();
      Failure& f = failures[worker];
      for (unsigned repeat = 0; repeat < 2000 && !f.failed; ++repeat) {
        for (unsigned width : {32u, 64u}) {
          for (unsigned bit = 0; bit < width; ++bit) {
            const uint64_t power = uint64_t(1) << bit;
            if (!test_value(width, power, width - bit - 1, f)) return;
            if (bit > 0 && !test_value(width, power - 1, width - bit, f)) return;
            if (bit > 0 && !test_value(width, power + 1, width - bit - 1, f)) return;
          }
        }
      }
    });
  }
  go.store(true, std::memory_order_release);
  for (auto& worker : workers) worker.join();
  bool failed = false;
  for (unsigned i = 0; i < 8; ++i) {
    const Failure& f = failures[i];
    if (!f.failed) continue;
    failed = true;
    std::printf("FAIL: worker=%u width=%u input=0x%llx expected=%u actual=%u\n",
                i, f.width, static_cast<unsigned long long>(f.value), f.expected, f.actual);
  }
  if (failed) return 1;
  std::puts("PASS: native 32/64-bit CLZ at power-of-two boundaries, eight concurrent threads");
  return 0;
}
