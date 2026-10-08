#include <sys/mman.h>
#include <unistd.h>
#include <cerrno>
#include <cassert>
#include <cstdint>
#include <cstdio>
using address=unsigned char*;using uintx=uintptr_t;using mincore_vec_t=char;
#define DEBUG_ONLY(x) x
#undef assert
#define assert(c,m) ((c)?(void)0:__builtin_trap())
template<class T,class U> T checked_cast(U u){return (T)u;}
bool is_aligned(uintptr_t n,size_t p){return !(n&(p-1));}
bool is_aligned(address n,size_t p){return is_aligned((uintptr_t)n,p);}
int solaris_mincore(char* p,size_t n,char* v){return ::mincore(p,n,(unsigned char*)v);}
struct os {static size_t vm_page_size(){return sysconf(_SC_PAGESIZE);}static bool committed_in_range(address,size_t,address&,size_t&);};
bool os::committed_in_range(address start, size_t size, address& committed_start, size_t& committed_size) {

#if !defined(LINUX) && !defined(SOLARIS)
  committed_start = start;
  committed_size = size;
  return true;
#else

  int mincore_return_value;
  constexpr size_t stripe = 1024;  // query this many pages each time
  mincore_vec_t vec [stripe + 1];

  // set a guard
  DEBUG_ONLY(vec[stripe] = 'X');

  size_t page_sz = os::vm_page_size();
  uintx pages = size / page_sz;

  assert(is_aligned(start, page_sz), "Start address must be page aligned");
  assert(is_aligned(size, page_sz), "Size must be page aligned");

  committed_start = nullptr;

  int loops = checked_cast<int>((pages + stripe - 1) / stripe);
  int committed_pages = 0;
  address loop_base = start;
  bool found_range = false;

  for (int index = 0; index < loops && !found_range; index ++) {
    assert(pages > 0, "Nothing to do");
    uintx pages_to_query = (pages >= stripe) ? stripe : pages;
    pages -= pages_to_query;

    // Get stable read
    int fail_count = 0;
    while ((mincore_return_value = solaris_mincore((char*)loop_base, pages_to_query * page_sz, vec)) == -1 && errno == EAGAIN){
      if (++fail_count == 1000){
        return false;
      }
    }

    // During shutdown, some memory goes away without properly notifying NMT,
    // E.g. ConcurrentGCThread/WatcherThread can exit without deleting thread object.
    // Bailout and return as not committed for now.
    if (mincore_return_value == -1 && errno == ENOMEM) {
      return false;
    }

    // If mincore is not supported.
    if (mincore_return_value == -1 && errno == ENOSYS) {
      return false;
    }

    assert(vec[stripe] == 'X', "overflow guard");
    assert(mincore_return_value == 0, "Range must be valid");
    // Process this stripe
    for (uintx vecIdx = 0; vecIdx < pages_to_query; vecIdx ++) {
      if ((vec[vecIdx] & 0x01) == 0) { // not committed
        // End of current contiguous region
        if (committed_start != nullptr) {
          found_range = true;
          break;
        }
      } else { // committed
        // Start of region
        if (committed_start == nullptr) {
          committed_start = loop_base + page_sz * vecIdx;
        }
        committed_pages ++;
      }
    }

    loop_base += pages_to_query * page_sz;
  }

  if (committed_start != nullptr) {
    assert(committed_pages > 0, "Must have committed region");
    assert(committed_pages <= int(size / page_sz), "Can not commit more than it has");
    assert(committed_start >= start && committed_start < start + size, "Out of range");
    committed_size = page_sz * committed_pages;
    return true;
  } else {
    assert(committed_pages == 0, "Should not have committed region");
    return false;
  }
#endif
}

int main(){size_t p=os::vm_page_size(), n=2200*p;address m=(address)mmap(nullptr,n,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);assert(m!=MAP_FAILED,"map");address s;size_t z=0;assert(!os::committed_in_range(m,n,s,z),"untouched");m[1023*p]=1;m[1024*p]=2;m[2199*p]=3;assert(os::committed_in_range(m,n,s,z)&&s==m+1023*p&&z==2*p,"stripe boundary");assert(os::committed_in_range(m+1025*p,n-1025*p,s,z)&&s==m+2199*p&&z==p,"tail");munmap(m,n);assert(!os::committed_in_range(m,n,s,z),"unmapped");puts("PASS: extracted Solaris stack residency scan, untouched pages, stripe boundaries, gaps and unmapping");}
