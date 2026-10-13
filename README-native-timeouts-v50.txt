v50: Solaris JNI thread-exit cleanup fix

Native evidence: native-timeout-results-20261013-011007.
The JNI native executable PID 4413 waits in pthread_join. Its worker LWP 2
remains in Solaris tsd_exit -> thr_setspecific at all three snapshots, while
worker LWP 3 has exited. This is distinct from VM creation or attach blocking.

HotSpot restores its pthread TLS key in restore_thread_pointer so other JNI
TLS destructors can call DetachCurrentThread. Solaris repeats destructor passes
while any key is repopulated. The old callback can therefore prevent an
attached native worker from finishing pthread_exit indefinitely.

Change: src/hotspot/os/posix/threadLocalStorage_posix.cpp bounds restorations
on Solaris to four passes (the POSIX minimum), then leaves the runtime-cleared
key clear. Explicit set_thread attach/detach resets the per-thread counter.
Other platforms retain their existing behavior. This does not automatically
detach native threads or destroy the VM, and does not change the jtreg test.

Verification: the actual changed source was compiled with minimal HotSpot
header stubs using g++ -std=c++17 -pthread -Wall -Wextra -Werror. A modeled
unbounded Solaris destructor loop stopped after five callbacks; restored TLS
remained available for a subsequent detach callback; a new TLS lifecycle
reset the counter; a real pthread worker exited and joined. Both Solaris and
non-Solaris source branches compiled. No native Solaris VM validation yet.

Remaining separate issue: TestStackBangMonitorOwned reaches STATUS:Passed
but VM shutdown stalls. PID 4411 has its VM Thread in safepoint synchronization
and its Signal Dispatcher in Threads::remove -> Mutex::lock_contended. No
safepoint timeout warning text was present in the supplied captures. This
package does not claim to fix that shutdown hang.

Apply the ZIP contents at the repository root, then:

  if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
    bash tests/capture-native-timeouts.sh
  else
    ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
    tail -40 /tmp/jdk25-build.log
  fi

The two original tests and their timeout limits are unchanged. Successful
completion of the JNI test must be reported by jtreg, not inferred from the
worker's printed output.
