v54: supply the inline Method definition required by frame_sparc.cpp

Native v53 link failure references Method::is_continuation_enter_intrinsic()
from frame_sparc.o. method.hpp declares that member inline, but its definition
is in method.inline.hpp. v53 introduced calls while retaining only the former
header. v54 replaces that include with oops/method.inline.hpp, which includes
the declaration header and provides the definition in the calling translation
unit. No runtime behavior or other source change is introduced versus v53.

Validated against the actual local JDK25 headers and the existing SPARC
sharedRuntime include pattern. Cumulative source retention, source hashes and
ZIP CRC checked. A native Solaris rebuild is still required. No clean build
is needed; the changed source should recompile frame_sparc.o.

Apply ZIP contents at the repository root and repeat:

  if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
    bash tests/run-continuation-repro.sh &&
      bash tests/run-mixed-yield-repro.sh &&
      bash tests/run-vector-memory-alignment-repro.sh &&
      bash tests/rerun-priority-crashes-v52.sh
  else
    ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
    tail -40 /tmp/jdk25-build.log
  fi

The v53 anchor correction has not yet run natively because that build failed
at link. Do not consider its continuation regression resolved until the smoke
passes on Solaris. v52's native-passing vector changes remain included.
