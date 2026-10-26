#!/usr/bin/env python3
"""Compile the actual SPARC double-register decoder and model scratch writes."""
from pathlib import Path
import re
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
source = root / 'src/hotspot/cpu/sparc'
if not source.exists():
    source = root.parent / 'verify/src/hotspot/cpu/sparc'
# A delivery ZIP overlays the source tree; the register header is unchanged.
header = source / 'register_sparc.hpp'
if not header.exists():
    header = root.parent / 'jdk25/cpu/sparc/register_sparc.hpp'
ad = (source / 'sparc.ad').read_text()
for rule, count in [('string_compress_fast', 3), ('string_inflate_fast', 4)]:
    text = ad.split('instruct ' + rule + '(', 1)[1].split('\n%}', 1)[0]
    assert '$$FloatRegister' not in text, rule
    for i in range(1, count + 1):
        assert f'reg_to_DoubleFloatRegister_object($ftmp{i}$$reg)' in text, (rule, i)
    if rule == 'string_inflate_fast':
        assert re.search(r'regD_low\s+ftmp1', text)
        assert re.search(r'regD_low\s+ftmp4', text)
body = re.search(r'friend inline FloatRegister as_DoubleFloatRegister\(int encoding\) \{(.*?)\n  \}',
                 header.read_text(), re.S).group(1)
cpp = r'''
#include <cassert>
#include <cstdio>
using FloatRegister = int;
int as_FloatRegister(int reg) { return reg; }
#undef assert
#define assert(condition, message) do { if (!(condition)) __builtin_abort(); } while (0)
int decode(int encoding) { BODY }
int main() {
  int checked = 0;
  for (int encoding = 0; encoding < 32; ++encoding) {
    int physical = (encoding & 1) ? 32 + (encoding & ~1) : encoding;
    assert(decode(encoding) == physical, "physical mapping");
    for (int live = 0; live < 32; ++live) {
      if (live == physical || live == physical + 1) continue;
      int bank[64]; for (int i=0; i<64; ++i) bank[i] = 1000+i;
      bank[decode(encoding)] = -1;
      bank[decode(encoding)+1] = -2;
      assert(bank[live] == 1000+live, "live float clobbered");
      ++checked;
    }
  }
  // Old $$FloatRegister decoding turns the upper-bank encoding 1 into F1.
  assert(decode(1) == 32 && 1 != decode(1), "old regression exposed");
  std::printf("PASS: %d decoder/live-float cases; AD double scratch operands and fpmerge constraints\n", checked);
}
'''.replace('BODY', body)
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp)
    (path / 'check.cpp').write_text(cpp)
    subprocess.run(['g++', '-std=c++17', '-Wno-builtin-macro-redefined', '-fsanitize=undefined',
                    str(path / 'check.cpp'), '-o', str(path / 'check')], check=True)
    subprocess.run([str(path / 'check')], check=True)
