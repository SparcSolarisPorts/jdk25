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
printf 'Forge Java: %s\n' "$(command -v java)"
# Check the actual selected VM and compact-header option before starting Forge.
java -Xmx256m -XX:+UseCompactObjectHeaders -version
cd "$server"
if [[ ${FORGE_TRACE:-0} == 1 ]]; then
  exec bash -x ./run.sh "$@"
fi
exec bash ./run.sh "$@"
