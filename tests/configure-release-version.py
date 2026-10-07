#!/usr/bin/env python3
"""Reuse the existing native configuration with a release-style version."""
import argparse
from pathlib import Path
import re
import shlex
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--source-dir', type=Path, default=Path(__file__).resolve().parent.parent)
parser.add_argument('--conf', default='solaris-sparcv9-server-release')
parser.add_argument('--print-only', action='store_true')
args = parser.parse_args()
root = args.source_dir.resolve()
spec = root / 'build' / args.conf / 'spec.gmk'
text = spec.read_text()
m = re.search(r'^CONFIGURE_COMMAND_LINE\s*:?=\s*(.*)$', text, re.M)
if not m:
    raise SystemExit('Cannot find CONFIGURE_COMMAND_LINE in ' + str(spec))
old = shlex.split(m.group(1))
version = re.search(r'^VERSION_NUMBER\s*:?=\s*(\d+(?:\.\d+){0,3})\s*$', text, re.M)
if version:
    number = version.group(1)
else:
    release = root / 'build' / args.conf / 'images/jdk/release'
    m = re.search(r'^JAVA_VERSION="(\d+(?:\.\d+){0,3})(?:[-+][^"]*)?"$', release.read_text(), re.M)
    if not m:
        raise SystemExit('Cannot determine the source build version; no configuration changed')
    number = m.group(1)
# Keep toolchain, boot JDK, JVM variants and existing platform options.
# Invoke configure with an argument vector; do not evaluate shell text.
old = [x for x in old if not x.startswith(('--with-version-', '--without-version-', '--with-vendor-name='))]
command = ['bash', str(root / 'configure'), *old,
           '--with-version-string=' + number + '+1',
           '--with-vendor-name=OpenJDK Solaris SPARC']
print(shlex.join(command), flush=True)
if not args.print_only:
    subprocess.run(command, cwd=root, check=True)
