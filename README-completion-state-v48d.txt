v48d completion-state diagnostics (no HotSpot source changes)

The native v48 basic continuation smoke passes all four modes. Mixed/C2
virtual-thread completion still fails. The test succeeds with test methods
interpreted and also with only test methods compiled by C2. C2 throughout
fails with OSR disabled. PreserveFramePointer (slow thaw) also fails, though
six workers terminate in that run. These comparisons do not prove a source
cause and are not proposed workarounds.

This update adds read-only reflection snapshots of unfinished virtual threads,
their Continuation (including inherited state) and up to eight stack chunks.
It records carrierThread, internal state, done, mounted and chunk geometry where
those fields exist. Snapshots are concurrent field reads, not atomic VM dumps.
It also prints uncaught exceptions and enables hidden frames in automatic JSON
dumps. No fields are changed; original untimed joins and PASS criteria remain.

Extract over the repository. No JDK rebuild is required.
Run: bash tests/run-mixed-yield-repro.sh

To print only the completion-state evidence through SSH:
out=$(ls -dt mixed-yield-results-*/ | head -1)
cat "$out/results.txt"
ggrep -E 'COMPLETION|^  (virtual|continuation|chunk)|STATE-DUMP-ERROR|UNCAUGHT|Exception|FAIL:|PASS:' "$out/mixed.log" "$out/c2.log"

Shell syntax and ZIP CRC were checked locally. No host javac is installed;
the runner compiles the Java diagnostic with the native JDK before testing.
The VM hang remains unresolved; this is a diagnostic tools update, not a fix.
