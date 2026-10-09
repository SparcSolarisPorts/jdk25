Mixed-yield diagnostic update v46b (test tools only)

The v46 native capture has main waiting in VirtualThread.joinNanos on a
CountDownLatch, no remaining ForkJoin worker threads, and an idle delay
scheduler. It does not contain the states/progress of the eight unmounted
virtual threads, so unfinished tasks cannot yet be distinguished from a
missed completion notification. No additional VM fix is claimed here.

Extract these files over the existing JDK repository. Rebuilding the VM is
not required; the script recompiles its Java test with the existing image.

Run: bash tests/run-mixed-yield-repro.sh

The original untimed joins remain intact. A platform daemon reports each
worker state and iteration count every five seconds, and fails the run after
90 seconds if the original joins have not returned. A separate GNU timeout
requests a thread dump at 180 seconds and kills the JVM 30 seconds later if
it still cannot exit. Each mode is bounded to about 3.5 minutes, excluding
javac compilation. Failure/timeout is retained as a nonzero exit.

All eight workers must finish all 20,000 iterations before PASS. The atomic
progress reporting adds diagnostic overhead and can change failure timing.
The Java test needs native JDK25 compilation/execution; only shell syntax
and ZIP CRC have been checked on the current host.

Upload the new mixed-yield-results directory, including mixed/c1/c2 logs
and results.txt. No core file is required.
