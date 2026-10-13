Collector correction only; no HotSpot source changes or JDK rebuild.

The previous collector missed JNI native child PID 4183 because its process
name filter only accepted lowercase java or an exeGetCreatedJavaVMs prefix.
This collector captures every descendant of the test runner, including native
executables regardless of their name. The two-test selection and jtreg timeout
factor are unchanged. Per-process pstack collection is bounded at 20 seconds.

SafepointTimeout and SafepointTimeoutDelay are product options in the checked
JDK source. The collector adds warning-only safepoint diagnostics through
JAVA_TOOL_OPTIONS for the Java runner and JNI-created native VMs. It does not
enable AbortVMOnSafepointTimeout or override test results.

Extract over the repository and run:
  bash tests/capture-native-timeouts.sh

Native stacks for TestStackBangMonitorOwned show JVM_Halt waiting for a VM
operation, VM Thread waiting to synchronize threads at a safepoint, and Signal
Dispatcher blocked in Mutex::lock_contended -> Threads::remove -> JavaThread::exit.
This identifies a shutdown/safepoint blocker, not yet a proved source fix.
JNI driver stacks show the child still alive; its native blocker was not captured.

Shell syntax and ZIP CRC passed locally. Native execution requires Solaris.
