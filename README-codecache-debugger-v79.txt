v79: correct the Solaris debugger capture; no VM source change
=============================================================
The native v78 ring starts at String.hashCode's inline-cache miss trap
(tne %xcc, instruction 0x93d03012). That trap is expected JVM control flow.
After debugger forwarding the fatal report shows SIGILL, SI_USER, sender
7124 (the debugger) instead of a hardware trap. The Solaris platform handler
rejects nonpositive si_code before decoding inline-cache traps. Stops 2-5
are SafeFetch probes made during fatal reporting, followed by abort.
Thus this capture does not reproduce the original unexplained exit 11.
Do not change String.hashCode or relax the VM's signal validation for it.

The new capture-unexpected-deopt-v79.sh reuses the original first action,
compiled classes and flags, with C2 enabled. It uses no signal catchpoints;
SIGSEGV/BUS/ILL/FPE/ABRT are nostop/noprint/pass. Instead it breaks at
VMError::report_and_die and os::abort, retaining up to four fatal-entry
stacks with arguments/registers/all-thread backtraces. There is no signal
reinjection command. This avoids v78's explicit signal-stop path, but native
Solaris/GDB validation is still required. An unhandled OS fault that bypasses
these functions may produce no fatal-entry file; keep gdb-console.log too.

No rebuild required:
  JDK25_JTREG_HOME=/export/home/solaris/tools/jtreg-8.2.1/jtreg \
    bash tests/capture-unexpected-deopt-v79.sh \
    priority-1-2-rerun-20261016-221049

Send the new text-only evidence.zip, or cat fatal-entry-*.log,
gdb-console.log, inferior-exit.txt and results.txt through SSH.
The capture remains capped at 180 seconds plus 10 seconds kill grace.
Debugger exit zero is not a jtreg pass. This replays only action 1;
the original four-action upstream test still needs a successful jtreg run.
The last original batch remains 25 passed and one failed.

Host checks: shell/Python syntax, generated GDB command inspection,
no signal catchpoints/reinjection in the new runner, and cumulative archive
CRC and source SHA-256 retention. No SPARC execution was performed here.
All v78 VM sources, fast paths and prior fixes are retained unchanged.
