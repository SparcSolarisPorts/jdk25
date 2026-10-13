// Host model using the exact v49 pending-return helper body.
// Does not execute generated SPARC assembly or validate native JVM behavior.
#include <cassert>
#include <cstdio>
#define INTPTR_FORMAT "%p"
#define log_debug(...) host_log
template<typename... Args> void host_log(const char*, Args...) {}
static void* p2i(void* p) { return p; }
#undef assert
#define assert(c, ...) do { if (!(c)) __builtin_abort(); } while (0)
struct Chunk { Chunk* up; bool empty; Chunk* parent() const { return up; } bool is_empty() const { return empty; } };
using stackChunkOop = Chunk*;
struct Cont { bool done; bool preempted; Chunk* tail; };
using oop = Cont*;
struct JavaThread;
struct ContinuationEntry { Cont* value; oop cont_oop(JavaThread*) const { return value; } };
struct JavaThread { ContinuationEntry* entry; ContinuationEntry* last_continuation() const { return entry; } };
struct jdk_internal_vm_Continuation {
 static bool done(oop c) { return c->done; }
 static bool is_preempted(oop c) { return c->preempted; }
 static Chunk* tail(oop c) { return c->tail; }
};
static int sparc_continuation_has_pending_return(JavaThread* thread) {
  ContinuationEntry* entry = thread->last_continuation();
  assert(entry != nullptr, "mounted continuation entry required");
  oop cont = entry->cont_oop(thread);
  if (jdk_internal_vm_Continuation::done(cont) ||
      jdk_internal_vm_Continuation::is_preempted(cont)) {
    return 0;
  }
  for (stackChunkOop chunk = jdk_internal_vm_Continuation::tail(cont);
       chunk != nullptr; chunk = chunk->parent()) {
    if (!chunk->is_empty()) {
      log_debug(continuations)("SPARC normal return resumes pending chunk: " INTPTR_FORMAT,
                               p2i(chunk));
      return 1;
    }
  }
  return 0;
}

int main() {
 Chunk parent{nullptr,false}, empty{&parent,true}, empty2{&empty,true};
 Cont cont{false,false,&empty}; ContinuationEntry entry{&cont}; JavaThread thread{&entry};
 assert(sparc_continuation_has_pending_return(&thread)==1); // observed empty head / pending parent
 cont.tail=&empty2; assert(sparc_continuation_has_pending_return(&thread)==1);
 cont.tail=&parent; assert(sparc_continuation_has_pending_return(&thread)==1);
 cont.done=true; assert(sparc_continuation_has_pending_return(&thread)==0);
 cont.done=false;cont.preempted=true;assert(sparc_continuation_has_pending_return(&thread)==0);
 cont.preempted=false;parent.empty=true;assert(sparc_continuation_has_pending_return(&thread)==0);
 cont.tail=nullptr;assert(sparc_continuation_has_pending_return(&thread)==0);
 std::puts("PASS: seven pending-return states, including empty head with pending parent, completed and preempted continuations");
}
