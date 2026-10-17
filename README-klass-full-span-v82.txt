v82: retain the full compressed-class encoding interval at high addresses
========================================================================
Native v81 validation: all three NMT wrappers pass. The generic wrapper
completes 1028 checks with 1027 passing, leaving CompressedKlass.basics_vm.
The single native check now gives the decisive assertion:
  encoding_range_end() - base(): 4026531839
  expected 4 GiB:                4294967296
v80's saturation avoided wrap but violated the endpoint API's full-span
contract. It is superseded here, without changing the upstream test.

Correction
On SPARC, during selection of a new encoding, if base + (1 << (bits+shift))
would overflow uintptr_t, lower the encoding base to the highest aligned
base that leaves the whole encoding interval representable. Do not move the
reserved class space, alter its size or change the chosen shift. Recalculate
valid narrow IDs afterward using the adjusted base, before any Klass uses
this encoding. A guarantee checks that actual class space is fully covered.
Normal non-overflowing encodings and other architectures are unchanged.
For the reported high range, a base of 0xffffffff10000000 becomes
0xfffffffefffffff8 (32-bit IDs, shift 0), giving endpoint
0xfffffffffffffff8 and the exact 4 GiB span, covering class range end
0xffffffff51000000. Generated encoding/decoding already supports arbitrary
Klass-aligned bases with addition/subtraction, so fast paths remain enabled.
The endpoint helper again reports base + full span instead of clipping.
Debug validation uses this same helper.

CDS initialize_for_given_encoding is deliberately not rebased: archived IDs
must keep their prescribed encoding. Newly selected encodings and newly
created archives use the corrected initialization. Rebuild images/test-image
as below, which also regenerates the image archives; do not reuse an old
external archive with a previously overflowing high-address encoding.

Validation here
- Compiled actual base selector and endpoint with undefined-behavior sanitizer:
  64 low/high/compact/normal geometries passed full-span and nonwrap checks;
  192 aligned Klass encode/decode roundtrips passed, including native case.
- Negative controls with old placement/clipping reject the exact contract.
- Existing 96 SafeFetch signed ABI/fault recovery model cases still pass.
- Cumulative archive source SHA-256 and CRC verified; all earlier files kept.
No native Solaris/SPARC execution was performed here. Native tests must confirm.
No test expectation or exclusion was modified.

After extracting at repository root:
  if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
    bash tests/rerun-gtest-v80.sh
  else
    tail -80 /tmp/jdk25-build.log
  fi
This keeps existing build job defaults; full gtest directory uses 16 test jobs
and a 30-minute cap. If it fails, send the new text-only evidence.zip.
The 29 jcstress categories passed before these SafeFetch/class metadata fixes;
repeat them and the earlier 26-case regression batch after gtest passes.
