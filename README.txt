HotSpot tier 1 triage — 2026-10-26 run
======================================
Native run: hotspot-tier1-20261026-223718-BQDO_d
Console observations: 1417 passed, 58 failed, 66 error (124 unsuccessful).
Selected: 2441. No final jtreg summary was produced, so the disposition of
all remaining selected tests (including platform filters) is not established.
The jtreg/timeout pipeline returned 134, not the time-limit status 124.
The log ends at about 2237 seconds (37 minutes), before the 2-hour cap.

Important evidence
At about 41% of selected cases, jspawnhelper reports:
  Cannot map /lib/sparcv9/ld.so.1
A cluster of errors follows. This points to a process mapping/resource issue
or an address-space problem and can contaminate multiple test outcomes.
It does not prove every failure has that cause. Five failures were already
reported before the first gc/gtests errors:
  compiler/c2/Test8004741.java
  compiler/c2/TestMergeStoresMemorySegment.java#byte-array
  compiler/codecache/CheckSegmentedCodeCache.java
  compiler/classUnloading/methodUnloading/TestMethodUnloading.java
  compiler/loopopts/TestDeadIrreducibleLoopsMain.java#id3

The final timeout message says its monitored command dumped core. That command
was the JDK21 jtreg harness; its own hs_err report is therefore important,
as well as reports from JDK25 child VMs. The console does not identify the
fatal frame or JRE version. Do not infer either from thread IDs alone.
Many prior focused tests passed. This transcript is not a prior-versus-current
matched tier1 comparison, so it does not establish 124 separate regressions.
It does establish 124 unsuccessful reported cases that need investigation.

Next action: collect the original evidence, without rerunning or rebuilding.
Extract this tools ZIP at ~/git/jdk25, then run:
  cd ~/git/jdk25
  python3 tests/collect-hotspot-tier1-evidence.py \
    hotspot-tier1-20261026-223718-BQDO_d

Send its printed tier1-text-evidence.zip. The collector reads nonpassed JTRs,
retained failing gtest assertions and recent hs_err logs, including harness
reports at repository root/make and /tmp. It never reads core files or heap
dumps. Individual files and the total input text are capped (48 MiB); every
truncation/omission is listed. Compression should keep normal text evidence
far smaller than the retained work directory. Current swap/limit/process
readings are explicitly current snapshots, not historical measurements.

This is a diagnostic tools package. It changes no VM source, test expectation,
problem list, compiler mode, test concurrency or timeout setting. The attached
124-case list is a record of reported failures/errors, not a full-suite pass
claim or the list of every case that did not complete.
