#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
jdk=${JDK25_IMAGE:-"$root/build/solaris-sparcv9-server-release/images/jdk"}
project=${1:?Usage: run-gradle-with-jdk25.sh PROJECT_DIR [Gradle arguments]}
shift
jdk=$(cd "$jdk" && pwd)
project=$(cd "$project" && pwd)
[[ -x "$jdk/bin/java" ]] || { echo "Missing Java executable: $jdk/bin/java" >&2; exit 1; }
[[ -f "$project/gradlew" ]] || { echo "Missing Gradle wrapper: $project/gradlew" >&2; exit 1; }
export JAVA_HOME="$jdk"
export PATH="$jdk/bin:$PATH"
echo "Gradle Java: $JAVA_HOME/bin/java"
"$JAVA_HOME/bin/java" -version
cd "$project"
if (($# == 0)); then set -- runServer; fi
exec bash ./gradlew "-Dorg.gradle.java.home=$JAVA_HOME" "$@"
