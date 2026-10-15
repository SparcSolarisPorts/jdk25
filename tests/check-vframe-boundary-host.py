#!/usr/bin/env python3
"""Compile the actual SPARC boundary predicate against a minimal host model.
This verifies scope selection and guards, not native frame walking or GC.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = root / 'src/hotspot/share/runtime/vframe.inline.hpp'
# Support the delivery staging layout during package construction.
if not source.exists():
    source = root.parent / 'verify/src/hotspot/share/runtime/vframe.inline.hpp'
s = source.read_text()
a = s.index('inline bool vframe_is_virtual_thread_continuation_entry(')
start = s.index('{', a)
depth = 1
end = start + 1
while depth:
    depth += (s[end] == '{') - (s[end] == '}')
    end += 1
predicate = s[a:end]
model = r'''
#include <cassert>
#include <cstdint>
#include <vector>
using oop = void*;
namespace vmIntrinsics { enum ID { other, _Continuation_enter }; }
struct Method { vmIntrinsics::ID id; auto intrinsic_id() const { return id; } };
struct frame { intptr_t* p; intptr_t* sp() const { return p; } };
struct ContinuationEntry {
 intptr_t* sp; oop continuation;
 oop cont_oop(void*) const { return continuation; }
};
struct JavaThread { std::vector<ContinuationEntry*> entries; };
struct RegisterMap {
 bool heap; oop continuation; JavaThread* jt;
 bool in_cont() const { return heap; }
 oop cont() const { return continuation; }
 JavaThread* thread() const { return jt; }
};
static int virtual_scope, custom_scope, virtual_cont, custom_cont;
struct java_lang_VirtualThread { static oop vthread_scope() { return &virtual_scope; } };
struct Continuation {
 static ContinuationEntry* get_continuation_entry_for_sp(JavaThread* t, intptr_t* sp) {
  for (auto entry : t->entries) if (entry->sp > sp) return entry;
  return nullptr;
 }
 static oop continuation_scope(oop c) {
  assert(c == &virtual_cont || c == &custom_cont);
  return c == &virtual_cont ? &virtual_scope : &custom_scope;
 }
};
'''
checks = r'''
int main() {
 intptr_t stack[1024] = {};
 Method enter{vmIntrinsics::_Continuation_enter}, other{vmIntrinsics::other};
 ContinuationEntry inner{stack + 200, &custom_cont}, outer{stack + 800, &virtual_cont};
 JavaThread nested{{&inner, &outer}};
 RegisterMap mounted{false, nullptr, &nested};
 assert(!vframe_is_virtual_thread_continuation_entry(frame{stack+100}, &mounted, &enter));
 assert(vframe_is_virtual_thread_continuation_entry(frame{stack+400}, &mounted, &enter));
 assert(!vframe_is_virtual_thread_continuation_entry(frame{stack+900}, &mounted, &enter));
 RegisterMap virtual_chunk{true, &virtual_cont, nullptr}, custom_chunk{true, &custom_cont, nullptr};
 assert(vframe_is_virtual_thread_continuation_entry(frame{nullptr}, &virtual_chunk, &enter));
 assert(!vframe_is_virtual_thread_continuation_entry(frame{nullptr}, &custom_chunk, &enter));
 RegisterMap no_thread{false, nullptr, nullptr}, empty_chunk{true, nullptr, nullptr};
 assert(!vframe_is_virtual_thread_continuation_entry(frame{nullptr}, &no_thread, &enter));
 assert(!vframe_is_virtual_thread_continuation_entry(frame{nullptr}, &empty_chunk, &enter));
 assert(!vframe_is_virtual_thread_continuation_entry(frame{nullptr}, &no_thread, &other));
}
'''
with tempfile.TemporaryDirectory(prefix='vframe-boundary-check-') as tmp:
    p = Path(tmp)
    (p/'check.cpp').write_text(model + predicate + checks)
    subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                    str(p/'check.cpp'), '-o', str(p/'check')], check=True)
    subprocess.run([str(p/'check')], check=True)
print('PASS: actual predicate; mounted/chunk scopes, nested entries, missing entry and ordinary methods')
