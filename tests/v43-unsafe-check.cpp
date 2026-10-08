#include <cstdint>
#include <cstring>
#include <cassert>
#include <cstdio>
#include <type_traits>
using u1=unsigned char;
#define ATTRIBUTE_NO_UBSAN
struct GuardUnsafeAccess { GuardUnsafeAccess(void*) {} };
bool is_aligned(uintptr_t p,size_t a){return (p & (a-1))==0;}
template<class T> struct Probe { void* _thread=nullptr; volatile T* pointer;
volatile T* addr(){return pointer;}
T normalize_for_read(T x){return x;} T normalize_for_write(T x){return x;}
  T get() {
    GuardUnsafeAccess guard(_thread);
#ifdef SPARC
    volatile T* p = addr();
    if (!is_aligned((uintptr_t)p, sizeof(T))) {
      T value;
      u1* bytes = reinterpret_cast<u1*>(&value);
      volatile u1* source = reinterpret_cast<volatile u1*>(p);
      for (size_t i = 0; i < sizeof(T); ++i) bytes[i] = source[i];
      return normalize_for_read(value);
    }
#endif
    return normalize_for_read(*addr());
  }

  // we use this method at some places for writing to 0 e.g. to cause a crash;
  // ubsan does not know that this is the desired behavior
  ATTRIBUTE_NO_UBSAN
  void put(T x) {
    GuardUnsafeAccess guard(_thread);
#ifdef SPARC
    volatile T* p = addr();
    if (!is_aligned((uintptr_t)p, sizeof(T))) {
      T value = normalize_for_write(x);
      const u1* bytes = reinterpret_cast<const u1*>(&value);
      volatile u1* destination = reinterpret_cast<volatile u1*>(p);
      for (size_t i = 0; i < sizeof(T); ++i) destination[i] = bytes[i];
      return;
    }
#endif
    *addr() = normalize_for_write(x);
  }};
template<class T> void check() {
 alignas(16) unsigned char storage[64];
 for(int offset=0;offset<16;offset++) {
  memset(storage, 0xa5, sizeof(storage));
  T want; unsigned char bytes[sizeof(T)];
  for(size_t i=0;i<sizeof(T);i++) bytes[i]=(unsigned char)(0xc1+i*17);
  memcpy(&want,bytes,sizeof(T)); Probe<T> p; p.pointer=(volatile T*)(storage+16+offset);
  p.put(want); T got=p.get(); assert(!memcmp(&got,&want,sizeof(T)));
  assert(storage[15+offset]==0xa5 && storage[16+offset+sizeof(T)]==0xa5);
 }
}
int main(){check<int16_t>();check<uint16_t>();check<int32_t>();check<int64_t>();check<float>();check<double>();puts("PASS: extracted native Unsafe methods, all alignments and bit patterns");}
