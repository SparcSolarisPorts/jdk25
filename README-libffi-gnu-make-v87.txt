v87: use GNU make during libffi configure; stop on the first failure
==================================================================
The Solaris v86 dependency build failed during config.status's automatic
make dependency bootstrap. It selected Solaris make before the script's
later gmake invocation. The missing ffitarget.h error was downstream of
that incomplete configuration.

The existing tests/build-libffi-v86.sh now exports MAKE=gmake to configure
and disables dependency tracking for this one-time dependency build. Every
configure, build and install step explicitly stops on failure. This is
necessary because Bash suppresses set -e inside the if-tested subshell used
to capture and display the build log. The original failing script therefore
incorrectly continued into gmake/install/cp after configure had failed.
The original failure status is now preserved. No build-job override added.

The Panama bridge and VM sources are unchanged from v86. This ZIP is
cumulative. Retry the same command after extraction:
  cd ~/git/jdk25
  bash tests/build-libffi-v86.sh &&
    bash tests/configure-panama-v86.sh &&
    if gmake images test-image > /tmp/jdk25-build.log 2>&1; then
      bash tests/run-panama-native-repro.sh
    else
      ggrep -n -B 4 -A 8 'error:' /tmp/jdk25-build.log
      tail -40 /tmp/jdk25-build.log
    fi

No need to repair the previous /tmp source tree; the script creates a fresh
one. It retains the pinned archive SHA-256 and private tools prefix.
Host mocked workflow checks cover successful configure/build/install and
configure, compile, install and checksum failures. They verify GNU make,
64-bit flags, disabled dependency tracking, and that later stages never run
after a failure. A native Solaris retry is still required.
