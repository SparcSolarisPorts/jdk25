#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
server=${1:?Usage: bash tests/run-forge-with-jdk25.sh /path/to/server [server arguments]}
shift
jdk=$(cd "$jdk" && pwd)
server=$(cd "$server" && pwd)
export JAVA_HOME="$jdk"
export PATH="$JAVA_HOME/bin:$PATH"
# SPARC register-window/interpreter frames need more stack than the reaper's
# small dedicated stack can provide during completion and shutdown. Use the
# normal VM thread-stack size; preserve existing Java launcher options.
export JDK_JAVA_OPTIONS="${JDK_JAVA_OPTIONS:+$JDK_JAVA_OPTIONS }-Djdk.lang.processReaperUseDefaultStackSize=true"
printf 'Forge Java: %s\n' "$(command -v java)"
printf 'Forge process reaper: using the default VM thread stack\n'
# Check the actual selected VM and compact-header option before starting Forge.
java -Xmx256m -XX:+UseCompactObjectHeaders -version
cd "$server"
if [[ ${FORGE_TRACE:-0} == 1 ]]; then
  exec bash -x ./run.sh "$@"
fi
exec bash ./run.sh "$@"
