v50a: deliver safepoint diagnostics to the actual jtreg /othervm child

Tools only; keep the v50 VM. No rebuild is needed.

The supplied 20261013-013215 report has empty test.vm.opts and no
JAVA_TOOL_OPTIONS pickup in TestStackBangMonitorOwned's System.err. The
JAVA_TOOL_OPTIONS pickups in the runner summary are other JVMs. Passing
flags only through that environment variable did not enable the intended
safepoint diagnostics in the failing test JVM.

rerun-priority-1-2.sh now accepts JDK25_SAFEPOINT_DIAGNOSTICS=1 and passes
-vmoption:-XX:+SafepointTimeout and
-vmoption:-XX:SafepointTimeoutDelay=2000 directly to jtreg. Normal reruns
retain their original options. The native collector enables these options
and selects only TestStackBangMonitorOwned; the JNI case already passed.
The test body, compilation settings, and timeoutFactor=4 remain unchanged.

Validated: bash syntax and a mock jtreg launcher capturing the actual runner
argument array, with diagnostics enabled and disabled. The OpenJDK jtreg FAQ
documents -vmoption as applying to child VMs:
https://github.com/openjdk/jtreg/blob/master/src/share/doc/javatest/regtest/faq.md

Apply the two scripts at the repository root, then:

  bash tests/capture-native-timeouts.sh

Print only the resulting report first:

  out=$(ls -dt priority-1-2-rerun-*/ | head -1)
  cat "$out/work/compiler/uncommontrap/TestStackBangMonitorOwned.jtr"

Verify the report records SafepointTimeout in test.vm.opts and the rerun
command. The warnings should identify the JavaThread state still preventing
the shutdown safepoint. If no warning appears despite the recorded options,
send the complete report; that absence is itself useful evidence.

This is a diagnostic correction, not a new HotSpot fix. The confirmed native
status is 24 of the selected 25 cases passed across the recent runs. The
remaining test prints TEST PASSED/STATUS:Passed but its JVM shutdown times out.
