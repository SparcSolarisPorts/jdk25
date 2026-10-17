v83: non-wrapping prescribed CDS encoding windows on Solaris/SPARC
=================================================================
Complete native v82 evidence identifies the remaining assertion:
CompressedKlass.basics_vm, line 37: Klass end 0xffffffff41000000 is
above encoding end NULL. The wrapper completes 1028 checks, 1027 pass;
all three NMT wrappers pass. The original JTR display elided the assertion;
it is preserved in work/gtest/GTestWrapper/test_result.xml and pid output.

Root cause
v82 corrects freely selected encodings, but CDS can restore a prescribed
base/shift via initialize_for_given_encoding, bypassing that selector.
An archive mapping base of 0xffffffff00000000 plus the full 4 GiB span
wraps exactly to zero. Changing the restored base alone would invalidate
precomputed narrow Klass IDs. The fix must preserve the mapping-relative IDs.

Correction
- Implement SPARC check_klass_decode_mode so it rejects invalid shifts,
  ranges larger than their encoding span, and bases whose FULL encoding
  interval wraps. set_klass_decode_mode validates the restored mode too.
- The existing CDS reservation code already consults this mode check and
  relocates if the requested archive location cannot be used. That path
  retains narrow IDs relative to its new mapping base; no archive format or
  precomputed ID is changed, and CDS is not disabled.
- SPARC's non-zero-base reservation now asks the OS for a whole maximum
  encoding window, then immediately releases its unused suffix. This gives
  CDS a mapping base with room for every encoded value. Only the requested
  archive/class region stays reserved. This is virtual reservation, not a
  commitment of physical memory, and the temporary suffix is not retained.
- Existing unscaled/zero-based low-address fast paths remain first choices.
  v82's ordinary base adjustment, exact full-span API, SafeFetch signed
  returns/fault recovery and all earlier changes remain in the ZIP.
- No upstream test, filter, expectation or skip list changes.

Host validation
Actual new mode-check and reservation C++ compiled with undefined-behavior
sanitizer against mocked OS calls: 28 cases passed, including the precise
native high CDS base (must be rejected), a safe relocated high base, complete
window size, exact unused-tail release, preserved archived IDs, low-address
fast paths and allocation failure. Confirmed the actual shared CDS code calls
the check before reservation and uses platform reservation during relocation.
Existing 64 full-span geometry/192 Klass roundtrip cases and 96 SafeFetch
ABI/fault model cases pass. Negative controls reject v82's unchecked mode
and its nullptr-only non-zero-base reservation. Archive CRC/SHA-256 verified.
No Solaris/SPARC execution was possible here; native confirmation is required.

After extracting the cumulative ZIP at repository root:
  if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
    bash tests/rerun-gtest-v80.sh
  else
    tail -80 /tmp/jdk25-build.log
  fi
Use the same full-suite runner (16 test jobs, 30-minute cap); build jobs use
your configured defaults. Send its evidence.zip if the wrapper still fails.
After a gtest pass, rerun the 26-case regression batch and jcstress as broader
checks of this changed class/archive placement.
