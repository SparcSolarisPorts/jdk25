# Test dependencies

The recorded 29 jcstress failures and 24 gtest-wrapper failures happened before
the tests could run. These require test artifacts in addition to the JVM patch.

## Google Test

Get Google Test 1.14.0 source:

```bash
mkdir -p ~/tools
git clone --branch v1.14.0 --depth 1 https://github.com/google/googletest.git ~/tools/googletest-1.14.0
```

Rerun your existing `bash configure` command with all its original options,
adding `--with-gtest=/export/home/solaris/tools/googletest-1.14.0`. Keep the
existing boot JDK, toolchain, Solaris port and JVM configuration options.
Then run `gmake images test-image JOBS=8`. Do not simply run configure with only
the gtest option: that could lose the options used to build this port.

OpenJDK documents the source version and `--with-gtest` requirement at
https://github.com/openjdk/jdk25u-dev/blob/master/doc/building.md#running-tests

## jcstress

Check the `@Artifact` revision in your own checkout:

```bash
ggrep -n -A 5 '@Artifact' test/hotspot/jtreg/applications/jcstress/JcstressRunner.java
```

Obtain the matching `jcstress-tests-all` jar from your artifact supplier, or
build the matching OpenJDK jcstress source revision with Maven. The OpenJDK
jcstress project documents `mvn clean verify` and the resulting executable
test jar under `tests-all/target` at https://github.com/openjdk/jcstress .
This ZIP does not contain the external jar and does not substitute an arbitrary
version for the revision requested by your test source.

Supply the jar explicitly:

```bash
JCSTRESS_JAR=/absolute/path/to/jcstress-tests-all.jar bash tests/rerun-failed-233.sh
```

This sets the property explicitly requested by the recorded failure:
`jdk.test.lib.artifacts.jcstress-tests-all`. Installing the jar makes the tests
able to run; it does not establish that the concurrency tests pass.
