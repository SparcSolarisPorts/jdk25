// Exercise the shared minimum-stack routine invoked by Solaris init_2.
#include <cassert>
#include <algorithm>
#include <cstdint>
#include <iostream>
using jint=int;
constexpr size_t K=1024;
constexpr int JNI_OK=0,JNI_ERR=-1;
#define MAX2(a,b) std::max((a),(b))
size_t page_size=8192,guard_size=24*K,shadow_size=80*K;
size_t ThreadStackSize=1024,CompilerThreadStackSize=1024,VMThreadStackSize=1024;
size_t align_up(size_t v,size_t a){return (v+a-1)/a*a;}
struct Output {template<typename... T> void print_cr(const char*,T...) {}} output;
Output* tty=&output;
struct JavaThread {static size_t stack;static void set_stack_size_at_create(size_t n){stack=n;}};
size_t JavaThread::stack=0;
struct StackOverflow {static size_t stack_guard_zone_size(){return guard_size;}static size_t stack_shadow_zone_size(){return shadow_size;}};
struct os {
 static size_t _java_thread_min_stack_allowed,_compiler_thread_min_stack_allowed,_vm_internal_thread_min_stack_allowed,_os_min_stack_allowed;
 static size_t vm_page_size(){return page_size;}
 static jint set_minimum_stack_sizes();
};
size_t os::_java_thread_min_stack_allowed,os::_compiler_thread_min_stack_allowed,os::_vm_internal_thread_min_stack_allowed,os::_os_min_stack_allowed;
void reset(){os::_java_thread_min_stack_allowed=86*K;os::_compiler_thread_min_stack_allowed=104*K;os::_vm_internal_thread_min_stack_allowed=128*K;os::_os_min_stack_allowed=16*K;JavaThread::stack=0;ThreadStackSize=CompilerThreadStackSize=VMThreadStackSize=1024;}
jint os::set_minimum_stack_sizes() {

  _java_thread_min_stack_allowed = _java_thread_min_stack_allowed +
                                   StackOverflow::stack_guard_zone_size() +
                                   StackOverflow::stack_shadow_zone_size();

  _java_thread_min_stack_allowed = align_up(_java_thread_min_stack_allowed, vm_page_size());
  _java_thread_min_stack_allowed = MAX2(_java_thread_min_stack_allowed, _os_min_stack_allowed);

  size_t stack_size_in_bytes = ThreadStackSize * K;
  if (stack_size_in_bytes != 0 &&
      stack_size_in_bytes < _java_thread_min_stack_allowed) {
    // The '-Xss' and '-XX:ThreadStackSize=N' options both set
    // ThreadStackSize so we go with "Java thread stack size" instead
    // of "ThreadStackSize" to be more friendly.
    tty->print_cr("\nThe Java thread stack size specified is too small. "
                  "Specify at least %zuk",
                  _java_thread_min_stack_allowed / K);
    return JNI_ERR;
  }

  // Make the stack size a multiple of the page size so that
  // the yellow/red zones can be guarded.
  JavaThread::set_stack_size_at_create(align_up(stack_size_in_bytes, vm_page_size()));

  // Reminder: a compiler thread is a Java thread.
  _compiler_thread_min_stack_allowed = _compiler_thread_min_stack_allowed +
                                       StackOverflow::stack_guard_zone_size() +
                                       StackOverflow::stack_shadow_zone_size();

  _compiler_thread_min_stack_allowed = align_up(_compiler_thread_min_stack_allowed, vm_page_size());
  _compiler_thread_min_stack_allowed = MAX2(_compiler_thread_min_stack_allowed, _os_min_stack_allowed);

  stack_size_in_bytes = CompilerThreadStackSize * K;
  if (stack_size_in_bytes != 0 &&
      stack_size_in_bytes < _compiler_thread_min_stack_allowed) {
    tty->print_cr("\nThe CompilerThreadStackSize specified is too small. "
                  "Specify at least %zuk",
                  _compiler_thread_min_stack_allowed / K);
    return JNI_ERR;
  }

  _vm_internal_thread_min_stack_allowed = align_up(_vm_internal_thread_min_stack_allowed, vm_page_size());
  _vm_internal_thread_min_stack_allowed = MAX2(_vm_internal_thread_min_stack_allowed, _os_min_stack_allowed);

  stack_size_in_bytes = VMThreadStackSize * K;
  if (stack_size_in_bytes != 0 &&
      stack_size_in_bytes < _vm_internal_thread_min_stack_allowed) {
    tty->print_cr("\nThe VMThreadStackSize specified is too small. "
                  "Specify at least %zuk",
                  _vm_internal_thread_min_stack_allowed / K);
    return JNI_ERR;
  }
  return JNI_OK;
}

int main(){
 int cases=0;
 for(size_t pages: {size_t(4096),size_t(8192),size_t(65536)}) {
  page_size=pages;guard_size=3*align_up(4096,pages);shadow_size=align_up(80*K,pages);
  size_t expected=align_up(86*K+guard_size+shadow_size,pages);
  reset();ThreadStackSize=(expected/K)-1;assert(os::set_minimum_stack_sizes()==JNI_ERR);cases++;
  reset();ThreadStackSize=expected/K;assert(os::set_minimum_stack_sizes()==JNI_OK);assert(os::_java_thread_min_stack_allowed==expected);assert(JavaThread::stack==expected);cases++;
  reset();ThreadStackSize=513;assert(os::set_minimum_stack_sizes()==JNI_OK);assert(JavaThread::stack==align_up(513*K,pages));cases++;
  reset();ThreadStackSize=0;assert(os::set_minimum_stack_sizes()==JNI_OK);assert(JavaThread::stack==0);cases++;
  reset();CompilerThreadStackSize=1;assert(os::set_minimum_stack_sizes()==JNI_ERR);cases++;
  reset();VMThreadStackSize=1;assert(os::set_minimum_stack_sizes()==JNI_ERR);cases++;
 }
 std::cout<<"PASS: "<<cases<<" minimum/guard/shadow, -Xss and VM/compiler stack cases\n";
}
