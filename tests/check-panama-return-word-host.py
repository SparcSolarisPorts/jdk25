#!/usr/bin/env python3
"""Exercise actual fallback result-conversion C helpers with bounds guards.
Also model the big-endian layout that makes the original direct ffi_call unsafe.
This does not execute SPARC code or validate its calling convention."""
from pathlib import Path
import tempfile, subprocess
root=Path(__file__).resolve().parents[1]
if not (root/'src/java.base/share/native/libfallbackLinker/fallbackLinker.c').exists() and not (root/'verify').exists():
    root=root.parent
source=root/'verify/src/java.base/share/native/libfallbackLinker/fallbackLinker.c'
if not source.exists():source=root/'src/java.base/share/native/libfallbackLinker/fallbackLinker.c'
s=source.read_text();a=s.index('static int needs_ffi_arg_result(');b=s.index('\nJNIEXPORT void JNICALL',a)
helpers=s[a:b]
h='''#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
typedef uint64_t ffi_arg;typedef int64_t ffi_sarg;
typedef struct { size_t size; unsigned short type; } ffi_type;
enum {FFI_TYPE_UINT8, FFI_TYPE_SINT8, FFI_TYPE_UINT16, FFI_TYPE_SINT16, FFI_TYPE_UINT32, FFI_TYPE_SINT32, FFI_TYPE_INT, FFI_TYPE_FLOAT, FFI_TYPE_STRUCT, FFI_TYPE_VOID};
'''
t='''
int main(void) {
  size_t count=0;
  const uint64_t values[]={0,1,0x7f,0x80,0xff,0x7fff,0x8000,0xffff,0x7fffffff,0x80000000,0xffffffff,UINT64_MAX};
  for(unsigned short type=0;type<=FFI_TYPE_INT;type++) {
    ffi_type ft={type<=FFI_TYPE_SINT8?1:type<=FFI_TYPE_SINT16?2:4,type};
    assert(needs_ffi_arg_result(&ft));
    for(size_t i=0;i<sizeof(values)/sizeof(values[0]);i++) {
      unsigned char buf[32];memset(buf,0x5a,sizeof(buf));
      unpack_ffi_arg(buf+7,values[i],&ft); // deliberately not word aligned
      for(int k=0;k<32;k++)if(k<7||k>=7+(int)ft.size)assert(buf[k]==0x5a);
      uint64_t expected;
      if(type==FFI_TYPE_SINT8)expected=(ffi_arg)(int64_t)(int8_t)values[i];
      else if(type==FFI_TYPE_SINT16)expected=(ffi_arg)(int64_t)(int16_t)values[i];
      else if(type==FFI_TYPE_SINT32||type==FFI_TYPE_INT)expected=(ffi_arg)(int64_t)(int32_t)values[i];
      else expected=values[i]&((UINT64_C(1)<<(8*ft.size))-1);
      assert(pack_ffi_arg(buf+7,&ft)==expected);++count;
    }
  }
  ffi_type f={4,FFI_TYPE_FLOAT},st={4,FFI_TYPE_STRUCT},v={0,FFI_TYPE_VOID};
  assert(!needs_ffi_arg_result(&f)&&!needs_ffi_arg_result(&st)&&!needs_ffi_arg_result(&v));
  printf("PASS: %zu actual C return conversions with buffer guards and signed/unsigned values\\n",count);
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'test.c';p.write_text(h+helpers+t);exe=Path(d)/'test'
 subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
# Reproduce byte positioning in a SPARC64 ffi_arg versus a Java layout buffer.
for size in (1,2,4):
 value=(1<<(size*8))-1
 word=value.to_bytes(8,'big')
 layout=value.to_bytes(size,'big')
 assert word[:size]!=layout and word[8-size:]==layout
print('PASS: big-endian word/layout placement model (1, 2, 4-byte results)')
