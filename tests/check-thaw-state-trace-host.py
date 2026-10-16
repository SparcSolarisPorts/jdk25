#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
stage=root if (root/'src/hotspot').exists() else root.parent/'verify'
s=(stage/'src/hotspot/share/runtime/continuationFreezeThaw.cpp').read_text();a=s.index('static inline void sparc_trace_thaw_state');b=s.index('static inline void thaw_sparc_restore_caller_window',a);fn=s[a:b]
model=r'''
#include <cstdint>
#include <cassert>
#include <cstdarg>
using uintptr_t=std::uintptr_t;
#define PTR_FORMAT "%zx"
struct JavaThread{};struct ContinuationEntry{};
struct oopDesc{bool done;};using oop=oopDesc*;
struct Chunk{bool empty;Chunk* par;bool is_empty(){return empty;}Chunk* parent(){return par;}};using stackChunkOop=Chunk*;
struct jdk_internal_vm_Continuation{static bool done(oop p){return p->done;}};
static bool enabled=true;static int records=0;
#define log_is_enabled(a,b) enabled
#define log_debug(a) logger
static void logger(const char*,...){++records;}
static uintptr_t p2i(void* p){return reinterpret_cast<uintptr_t>(p);}
'''
checks=r'''
int main(){JavaThread t;ContinuationEntry e;oopDesc cont{false};Chunk parent{false,nullptr},chunk{true,&parent};
 for(oop c:{static_cast<oop>(nullptr),&cont})for(stackChunkOop ch:{static_cast<stackChunkOop>(nullptr),&chunk,&parent})
  sparc_trace_thaw_state("check",&t,&e,c,ch);
 assert(records==6);enabled=false;
 sparc_trace_thaw_state("off",&t,&e,reinterpret_cast<oop>(1),reinterpret_cast<stackChunkOop>(1));
 assert(records==6);
}
'''
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);(d/'check.cpp').write_text('#include <initializer_list>\n'+model+fn+checks)
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(d/'check.cpp'),'-o',str(d/'check')],check=True)
 subprocess.run([str(d/'check')],check=True)
a=s.index('static inline int prepare_thaw_internal(JavaThread* thread, bool return_barrier) {');p=s[a:s.index('class ThawBase',a)]
assert p.index('guarantee(chunk != nullptr')<p.index('if (UNLIKELY(chunk->is_empty()))')
a=p.index('chunk = chunk->parent();');assert p.index('guarantee(chunk != nullptr',a)<p.index('assert(!chunk->is_empty()',a)
print('PASS: actual transition helper null/valid states, tracing-off no dereference, guards before chunk access')
