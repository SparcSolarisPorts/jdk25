v70 single-carrier sleep diagnostic — no VM source changes

The SuspendResume2 .jtr from 20261016-002828 records a real 480-second
execution timeout. It has not reached TestSuspendResume(): the main test
thread is in start_thread -> ensureReady while the only scheduler carrier
is occupied by a virtual worker in Thread.sleep -> parkOnCarrierThread.
This identifies a progress/pinning problem during worker startup; the
actual JVMTI suspend/resume functions have not been tested by this run.
The cause of the pin is not established by that stack dump alone.

This small reproduction starts exactly 20 virtual workers on a scheduler
with both parallelism and maxPoolSize set to one. Each worker performs a
hot loop and sleeps until the main thread has verified all workers started
and each made progress. If a worker pins the sole carrier indefinitely,
the main thread fails after 15 seconds rather than waiting eight minutes.
This is a separate diagnostic; the upstream jtreg tests are unchanged.

Four compiler modes run both without an agent and with the existing
SuspendResume2 native agent (eight cases). The diagnostic never invokes
that agent's suspend/resume JNI functions: it isolates startup, callbacks,
ordinary continuation yield, and sleeping. The supplied agent records up
to 20 virtual-thread starts, so do not increase this diagnostic's worker
count or add additional virtual tasks when using that agent.

JFR records jdk.VirtualThreadPinned with threshold zero and stack traces;
up to 12 events are printed per case, along with every worker's progress.
A passing case confirms single-carrier startup and sleep progress only,
not the correctness of the agent's uninvoked suspend/resume functions.

Extract this ZIP over ~/git/jdk25 and run against the current built image:

  cd ~/git/jdk25
  bash tests/run-single-carrier-sleep-repro.sh

No rebuild is required for these diagnostic files. If v69 source was
pulled but not rebuilt yet, finish that rebuild first to use its C2 growth
change. Its native CLZ/startup verification remains a separate check.

Each JVM has a 60-second limit plus five seconds for forced termination;
compilation is separately bounded. Normal cases should be quick, while
cases that reproduce starvation usually stop after 15 seconds plus cleanup.
Core dumps are disabled in the runner and its children only. evidence.zip
contains text logs and results, not cores, VM binaries or JFR binaries.
Send that evidence.zip. The small raw JFR recordings remain alongside it
if the text events prove insufficient.

Host validation: Java source compiles using the available JDK17 compiler;
reflection supplies virtual-thread creation only when running on the target
JDK. The shell runner passes bash -n. This Linux host cannot execute the
SPARC runtime, so native outcomes and the pinning cause remain pending.
This package is diagnostic, not a new cumulative VM patch.
