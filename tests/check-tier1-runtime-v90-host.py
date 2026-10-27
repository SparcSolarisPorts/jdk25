#!/usr/bin/env python3
"""Compile actual code-cache sizing logic and UTF-16 print guard on a host."""
from pathlib import Path
import re, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
src=root/'src/hotspot'
if not src.exists():src=root.parent/'verify/src/hotspot'
text=(src/'share/code/codeCache.cpp').read_text()
start=text.index('static void check_min_size(')
end=text.index('  FLAG_SET_ERGO(NonNMethodCodeHeapSize,', start)
production=text[start:end]+'''  result_cache=cache_size; result_n=non_nmethod.size;
  result_p=profiled.size; result_u=non_profiled.size;
  result_ps=ps;
}
'''
field=(src/'share/runtime/fieldDescriptor.cpp').read_text()
charblock=re.search(r'case T_CHAR:\s*\{(.*?)\n      \}',field,re.S).group(1)
cpu=(src/'cpu/sparc/vm_version_sparc.cpp').read_text()
assert '_cpu_info_string = _features_string;' in cpu
header=r'''
#include <algorithm>
#include <vector>
#include <stdexcept>
#include <string>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <cstdint>
using std::size_t;
constexpr size_t K=1024, M=K*K, G=M*K;
#define MAX2(a,b) std::max(a,b)
#define DEBUG_ONLY(x)
#define COMPILER1_PRESENT(x) x
#define COMPILER2_PRESENT(x) x
#define FLAG_IS_CMDLINE(v) v##_cmd
#define assert(c,msg) do {if(!(c)) throw std::runtime_error(msg);} while(0)
bool is_aligned(size_t a,size_t b){return (a&(b-1))==0;}
size_t align_up(size_t a,size_t b){return (a+b-1)&~(b-1);}
struct Logger { template<class... T> void operator()(T... args) {} };
#define log_debug(...) Logger{}
#define log_info(...) Logger{}
#define log_warning(...) Logger{}
#define PROPERFMT "%zu"
#define PROPERFMTARGS(x) x
bool UseLargePages=true;
struct err_msg {
 std::string s;
 template<class... T> err_msg(const char* f,T... a){char b[1024];if constexpr(sizeof...(a)==0)std::snprintf(b,sizeof b,"%s",f);else std::snprintf(b,sizeof b,f,a...);s=b;}
 template<class... T> void append(const char* f,T... a){char b[1024];if constexpr(sizeof...(a)==0)std::snprintf(b,sizeof b,"%s",f);else std::snprintf(b,sizeof b,f,a...);s+=b;}
 operator const char*() const {return s.c_str();}
};
void vm_exit_during_initialization(const char* a,const char* b){throw std::runtime_error(std::string(a)+": "+b);}
size_t NonNMethodCodeHeapSize,ProfiledCodeHeapSize,NonProfiledCodeHeapSize,ReservedCodeCacheSize;
bool NonNMethodCodeHeapSize_cmd,ProfiledCodeHeapSize_cmd,NonProfiledCodeHeapSize_cmd,ReservedCodeCacheSize_cmd;
size_t CodeCacheMinimumUseSpace=400*K, CODE_CACHE_SIZE_LIMIT=2*G;
bool profiling=true;size_t preferred_ps=4*M;
size_t result_cache,result_n,result_p,result_u,result_ps;
namespace os {
 bool support512=true;
 size_t vm_page_size(){return 8*K;}
 size_t vm_allocation_granularity(){return 8*K;}
 struct PageSizes {
  size_t next_smaller(size_t p)const{for(size_t n:{4*M,512*K,64*K,8*K})if(n<p && (support512 || n!=512*K))return n;return 0;}
 };
 const PageSizes& page_sizes(){static PageSizes pages;return pages;}
}
struct CompilationPolicy {static size_t c1_count(){return 1;}static size_t c2_count(){return 1;}};
struct Compiler {static size_t code_buffer_size(){return 512*K;}};
struct C2Compiler {static size_t initial_code_buffer_size(){return 512*K;}};
enum class CodeBlobType {MethodProfiled,MethodNonProfiled};
struct CodeCache {
 static bool heap_available(CodeBlobType b){return b!=CodeBlobType::MethodProfiled || profiling;}
 static size_t page_size(bool,size_t){return preferred_ps;}
 static void initialize_heaps();
};
'''
checks=r'''
void setup(size_t n,size_t p,size_t u,size_t total,bool total_set=true){
 NonNMethodCodeHeapSize=n;ProfiledCodeHeapSize=p;NonProfiledCodeHeapSize=u;ReservedCodeCacheSize=total;
 NonNMethodCodeHeapSize_cmd=ProfiledCodeHeapSize_cmd=NonProfiledCodeHeapSize_cmd=true;
 ReservedCodeCacheSize_cmd=total_set; profiling=true;preferred_ps=4*M;
}
int main(){
 int cases=0;
 // Three 10M segments must stay exactly 30M, even when default code pages are 4M.
 setup(10*M,10*M,10*M,240*M,false);CodeCache::initialize_heaps();
 assert(result_cache==30*M && result_ps==512*K,"30M byte-size preservation");++cases;
 for(bool tiered:{false,true})for(size_t n:{20*M,75*M,100*M}){
  size_t p=n==75*M?75*M:n;size_t u=n==75*M?50*M:n;
  setup(n,p,u,n+p+u);profiling=tiered;CodeCache::initialize_heaps();
  assert(result_cache==n+p+u && result_n==n,"explicit sizes");
  assert(tiered?(result_p==p && result_u==u):(result_p==0 && result_u==p+u),"profiled compatibility");++cases;
 }
 setup(16*M,16*M,16*M,48*M);CodeCache::initialize_heaps();
 assert(result_ps==4*M,"aligned large-page fast path must stay enabled");++cases;
 setup(10*M,10*M,10*M,100*M);ProfiledCodeHeapSize_cmd=NonProfiledCodeHeapSize_cmd=false;
 CodeCache::initialize_heaps();assert(result_p==45*M && result_u==45*M,"unset split");++cases;
 setup(10*M,10*M,10*M,100*M);NonNMethodCodeHeapSize_cmd=false;
 CodeCache::initialize_heaps();assert(result_n==80*M,"unset nonmethod");++cases;
 setup(6*M,5*M,5*M,10*M);bool rejected=false;
 try{CodeCache::initialize_heaps();}catch(const std::runtime_error& e){rejected=std::strstr(e.what(),"Invalid code heap sizes");}
 assert(rejected,"inconsistent explicit sizes remain rejected");++cases;
 setup(400*K,10*M,10*M,400*K);ProfiledCodeHeapSize_cmd=NonProfiledCodeHeapSize_cmd=false;rejected=false;
 try{CodeCache::initialize_heaps();}catch(const std::runtime_error& e){rejected=std::strstr(e.what(),"Not enough space in non-nmethod");}
 assert(rejected,"nonmethod minimum check retained");++cases;
 setup(3*G,10*M,10*M,240*M,false);rejected=false;
 try{CodeCache::initialize_heaps();}catch(const std::runtime_error& e){rejected=std::strstr(e.what(),"Code cache size exceeds platform limit");}
 assert(rejected,"platform limit retained");++cases;
 os::support512=false;
 setup(10*M,10*M,10*M,240*M,false);CodeCache::initialize_heaps();
 assert(result_cache==30*M && result_ps==64*K,"use next supported compatible size");++cases;
 os::support512=true;
 for(size_t a=1;a<=256;a++){
  CodeHeapInfo n={a*M,true,true},p={10*M,true,true},u={10*M,true,true};
  auto ps=code_heap_page_size(4*M,(a+20)*M,true,n,p,u);
  assert(is_aligned(a*M,ps)&&is_aligned((a+20)*M,ps)&&is_aligned(10*M,ps),"all boundaries fit");++cases;
 }
 std::printf("PASS: %d actual code-cache geometry/validation cases\n",cases);
}
'''
charcpp=r'''
#include <cstdint>
#include <cstdio>
#include <cstdlib>
using jchar=uint16_t;
int guarded_isprint(int c){if(c<0||c>255)std::abort();return c>=32&&c<=126;}
#define isprint(c) guarded_isprint(c)
struct Obj{jchar value; jchar char_field(int){return value;}};
struct Stream{int shown,number;void print(const char*,int c,int n){shown=c;number=n;}};
void print_char(Stream* st,Obj* obj){BODY}
int main(){
 Stream stream;Obj obj;
 for(unsigned i=0;i<65536;i++){
  obj.value=(jchar)i;print_char(&stream,&obj);
  if(stream.number!=(int)i||stream.shown!=((i>=32&&i<=126)?(int)i:' '))std::abort();
 }
 std::puts("PASS: all 65536 UTF-16 values preserve numeric output and stay within the ctype table");
}
'''.replace('BODY',charblock.replace('offset()','0'))
with tempfile.TemporaryDirectory() as d:
 d=Path(d)
 for name,code in [('geometry',header+production+checks),('chars',charcpp)]:
  (d/(name+'.cpp')).write_text(code)
  subprocess.run(['g++','-std=c++17','-Wall','-Werror','-fsanitize=undefined',str(d/(name+'.cpp')),'-o',str(d/name)],check=True)
  subprocess.run([str(d/name)],check=True)
