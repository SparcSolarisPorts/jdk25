v75: isolate spill-mask probe projections from the compiled graph
===============================================================
Root cause identified from the native v74 capture:
- All three startup modes fail before old-arena reclamation (stage=pre-reclaim).
- Projection 0 belongs to the old node arena (old=1), not compiler/resource
  storage. Matcher and current Compile/arena pointers agree.
- Its expand log initially has index=64, unique=65. Later projections have
  index=6/9/10 and unique=7/10/11, after matching resets node numbering.
- The first projection therefore precedes the node-arena swap. Its pointer
  persists when old storage is released, explaining the later UINT_MAX index.

Matcher::match first calls init_spill_mask. That calls
regmask_for_ideal_register, which matches synthetic loads only to discover
register masks. On SPARC, an ADLC expansion can append a DEF/KILL MachProjNode
for one of these probes to the same projection list used by the real graph.
The synthetic load is not part of the compiled graph. Retaining its projection
across the arena swap is a lifetime error; growing Block_Array cannot repair it.

The fix snapshots the projection count immediately before each synthetic
match_tree call and removes only the suffix appended by that probe immediately
after it returns. Cleanup precedes the compilation-failure return too. Existing
list entries, all projections produced by matching real instructions, the probe
result/register-mask pointer, and vector operand specialization are preserved.
This is SPARC-only. It does not clamp an invalid index, skip a real instruction,
disable C2, or weaken the arena/projection/Block_Array guards.

Retained v73/v74 checks should now accept real graph projections. Debug logs
will still show probe creation, but those entries must not survive into
pre-reclaim/post-match/GCM validation. The v69 bounds checks remain useful.

Host validation:
- Compiled the actual patched matching tail: 792 combinations per SPARC/generic
  build, varying existing prefix length, appended projections, failure/success
  and scalar/vector specialization. Checked mask identity and preserved live
  graph entries after simulated old-arena release.
- The previous matching tail fails that lifetime regression as expected.
- Actual projection verifier mock checks, shell syntax, cumulative source
  retention and ZIP CRC/SHA-256 passed.
Full Solaris/SPARC build and startup stress validation are still required.

After extraction, build normally with C2 enabled (no build-tool C1 override):
  if gmake images test-image JOBS=16 > /tmp/jdk25-build.log 2>&1; then
    JDK25_JTREG_HOME=/export/home/solaris/tools/jtreg-8.2.1/jtreg \
      JDK25_STARTUP_REPEATS=3 bash tests/capture-c2-startup.sh \
      priority-1-2-rerun-20261016-012229 &&
      JDK25_TEST_JOBS=16 bash tests/rerun-suspend-resume-v72.sh
  else
    tail -80 /tmp/jdk25-build.log
  fi
Nine startup probes are each capped at 30 seconds; the suspension batch has a
15-minute wall-clock cap. Failure or timeout remains failure, not a pass.

Native v72 previously passed all eight single-carrier modes with zero pin
JFR events and all 16 continuation regressions. The two suspension tests have
not yet run on that build because startup failed. The v68 monitor-driven
unmounting fallback limitation is unchanged. This package is cumulative.
