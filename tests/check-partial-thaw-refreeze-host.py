#!/usr/bin/env python3
"""Exercise the actual recursive freeze boundary body using mock frames."""
from pathlib import Path
import subprocess, tempfile, zipfile
root=Path(__file__).resolve().parents[1]
stage=root if (root/'src/hotspot').exists() else root.parent/'verify'
s=(stage/'src/hotspot/share/runtime/continuationFreezeThaw.cpp').read_text()
def extract(s):
 a=s.index('template<typename FKind>\ninline freeze_result FreezeBase::recurse_freeze_java_frame')
 b=s.index('inline void FreezeBase::before_freeze_java_frame',a)
 return s[a:b]
fn=extract(s)
model=r'''
#include <cstdio>
#include <cstdlib>
#define assert(c, msg) do { if (!(c)) std::abort(); } while (0)
#define NOT_PRODUCT(x) x
using intptr_t=long;
using freeze_result=int;
const int freeze_ok=0, freeze_pinned_native=1;
struct frame {
 intptr_t* s; intptr_t* u; intptr_t* bottom; int pc; bool special;
 intptr_t* sp()const{return s;} intptr_t* unextended_sp()const{return u;}
 int sender_pc()const{return pc;}
};
struct Continuation {
 static bool is_return_barrier_entry(int pc){return pc==42;}
 static bool is_continuation_enterSpecial(const frame& f){return f.special;}
};
struct Cont {intptr_t* entry; intptr_t* entrySP()const{return entry;}};
template<bool I> struct Kind {
 static constexpr bool interpreted=I;
 static bool is_instance(const frame&){return true;}
 static intptr_t* frame_bottom(const frame& f){return f.bottom;}
};
struct FreezeBase {
 int _freeze_size=0,_frames=0,sends=0,finalizes=0,recurses=0,saved_args=-1;
 intptr_t* _bottom_address; Cont _cont; frame next;
 int finalize_freeze(const frame&,frame&,int args){++finalizes;saved_args=args;return freeze_ok;}
 template<class K> frame sender(const frame&){++sends;return next;}
 int recurse_freeze(const frame& f,frame&,int args,bool,bool){++recurses;saved_args=args;return f.pc==99?freeze_pinned_native:freeze_ok;}
 template<class K> int recurse_freeze_java_frame(const frame&,frame&,int,int);
};
'''
checks=r'''
template<bool I> void run(){
 intptr_t stack[1024];
 for(int shift=0;shift<=128;shift+=2) for(int args=0;args<=16;++args){
  frame f{stack+128,stack+128,stack+400-shift,42,false},caller{};
  FreezeBase b{};b._bottom_address=stack+512;b._cont.entry=stack+512;
  b.next={stack+400-shift,stack+400-shift,stack+420,99,false};
  int result=b.recurse_freeze_java_frame<Kind<I>>(f,caller,32,args);
#ifdef SPARC
  assert(result==freeze_ok, "barrier should finalize");
  assert(b.finalizes==1 && b.sends==0 && b.recurses==0,"do not walk synthetic PC");
#else
  assert(result==freeze_pinned_native && b.sends==1 && b.recurses==1,"generic unchanged");
#endif
  assert(b._frames==1 && b._freeze_size==32 && b.saved_args==args,"accounting");
 }
 for(int pc: {7,99}){
  frame f{stack+128,stack+128,stack+400,7,false},caller{};
  FreezeBase b{};b._bottom_address=stack+512;b._cont.entry=stack+512;
  b.next={stack+400,stack+400,stack+420,pc,false};
  assert(b.recurse_freeze_java_frame<Kind<I>>(f,caller,32,8)==(pc==99?freeze_pinned_native:freeze_ok),"real caller");
  assert(b.finalizes==0 && b.recurses==1,"do not hide native or Java caller");
 }
 for(bool own: {false,true}){
  frame f{stack+128,stack+128,stack+400,7,false},caller{};
  FreezeBase b{};b._bottom_address=stack+512;b._cont.entry=stack+512;
  b.next={stack+400,stack+(own?512:450),stack+420,7,true};
  // Interpreted callers may have distinct SP and unextended SP.
  b.recurse_freeze_java_frame<Kind<true>>(f,caller,32,8);
#ifdef SPARC
  assert(b.finalizes==(own?1:0) && b.recurses==(own?0:1),"own versus nested entry");
#else
  assert(b.recurses==1,"generic entry behavior unchanged");
#endif
 }
}
int main(){run<true>();run<false>();puts("PASS: 2210 refreeze layouts plus Java/native callers and nested entries");}
'''
model='#include <initializer_list>\n'+model
with tempfile.TemporaryDirectory(prefix='sparc-refreeze-') as tmp:
 d=Path(tmp);src=d/'check.cpp';exe=d/'check'
 for flags in (['-DSPARC'],[]):
  src.write_text(model+fn+checks)
  subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',*flags,str(src),'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
