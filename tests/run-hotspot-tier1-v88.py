#!/usr/bin/env python3
"""Bound per-VM ergonomics while retaining 24 concurrent jtreg tests."""
import argparse
import collections
import datetime
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time


def stop_group(proc):
    # Clean up child test JVMs too, including after the harness has aborted.
    for sig, delay in ((signal.SIGTERM, 5), (signal.SIGKILL, 0)):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            break
        if delay:
            time.sleep(delay)
    proc.wait()


def run_live(command, env, log, deadline, progress=False):
    counts = collections.Counter()
    total = 0
    proc = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, start_new_session=True)
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    pending = b''
    last = time.monotonic()
    start = last
    timed_out = False
    last_resource = start - 30

    def show(line):
        nonlocal total
        if progress or not re.match(r'^\s*\S+\.(?:java|sh)(?:#[^\s]+)?\s*$', line):
            print(line, flush=True)
        match = re.search(r'Tests found:\s*([\d,]+)', line)
        if match:
            total = int(match.group(1).replace(",", ""))
        match = re.match(r'^(Passed:|FAILED:|Error:)\s+', line)
        if match:
            counts[match.group(1)] += 1

    def heartbeat():
        nonlocal last_resource
        if env.get('JDK25_RESOURCE_HISTORY') and time.monotonic() - last_resource >= 30:
            try:
                sample = subprocess.run(['/usr/bin/sh', '-c', '/usr/sbin/swap -s'], capture_output=True, text=True, timeout=2)
                with open(env['JDK25_RESOURCE_HISTORY'], 'a') as history:
                    history.write(datetime.datetime.now().isoformat() + ' ' + sample.stdout + sample.stderr)
            except (OSError, subprocess.TimeoutExpired) as error:
                with open(env['JDK25_RESOURCE_HISTORY'], 'a') as history:
                    history.write(str(error) + '\n')
            last_resource = time.monotonic()
        done = sum(counts.values())
        bar = ('=' * min(30, done * 30 // total)).ljust(30, '.') if total else '.' * 30
        elapsed = int(time.monotonic() - start)
        print(f'[{bar}] {done}/{total or "?"} PASS:{counts["Passed:"]} '
              f'FAIL:{counts["FAILED:"]} ERROR:{counts["Error:"]} '
              f'elapsed={elapsed // 60}m{elapsed % 60:02d}s', flush=True)

    # The selected count is provided by the preceding list-only invocation.
    total = int(env.get('JDK25_SELECTED_COUNT', '0'))
    try:
        with log.open('wb') as output:
            while selector.get_map():
                now = time.monotonic()
                if now >= deadline:
                    timed_out = True
                    print('Command wall-clock limit reached; unfinished tests are not passes.', flush=True)
                    stop_group(proc)
                    # Drain only the buffered pipe data after group termination.
                    deadline = float('inf')
                for key, _ in selector.select(timeout=1):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    output.write(chunk)
                    output.flush()
                    pending += chunk
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        show(line.decode(errors='replace'))
                if progress and time.monotonic() - last >= 10:
                    heartbeat()
                    last = time.monotonic()
            if pending:
                show(pending.decode(errors='replace'))
        rc = proc.wait()
    except BaseException:
        stop_group(proc)
        raise
    finally:
        selector.close()
        proc.stdout.close()
    if timed_out or rc != 0:
        stop_group(proc)
    if progress:
        heartbeat()
    return 124 if timed_out else (128 - rc if rc < 0 else rc), counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--failed', action='store_true', help='rerun all 124 originally unsuccessful cases')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    build = Path(os.environ.get('JDK25_BUILD', str(root / 'build/solaris-sparcv9-server-release')))
    jdk = Path(os.environ.get('JDK25_IMAGE', str(build / 'images/jdk')))
    jtreg = Path(os.environ.get('JDK25_JTREG_HOME', str(Path.home() / 'tools/jtreg-8.2.1/jtreg')))
    runner = Path(os.environ.get('JTREG_RUNNER_JAVA', '/usr/jdk/jdk-21/bin/java'))
    for path in (runner, jdk / 'bin/java', jtreg / 'lib/jtreg.jar'):
        if not path.is_file():
            parser.error(f'Missing required file: {path}')
    tests = ['test/hotspot/jtreg:tier1']
    if args.failed:
        tests = (root / 'tests/tier1-unsuccessful-v88.txt').read_text().splitlines()
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    out = Path(tempfile.mkdtemp(prefix=f'hotspot-tier1-v89-{stamp}-', dir=root))
    env = os.environ.copy()
    # JAVA_TOOL_OPTIONS reaches nested Java processes and JNI gtest VMs too.
    # These are ergonomic defaults, not fixed Xmx/Xms: explicit test flags win.
    defaults = '-XX:MaxRAM=2g -XX:InitialRAMPercentage=1.5625 -XX:MaxRAMPercentage=25 -XX:ActiveProcessorCount=8'
    env['JAVA_TOOL_OPTIONS'] = defaults + (' ' + env['JAVA_TOOL_OPTIONS'] if env.get('JAVA_TOOL_OPTIONS') else '')
    (out / 'environment.txt').write_text('JAVA_TOOL_OPTIONS=' + env['JAVA_TOOL_OPTIONS'] + '\n'
                                      + 'runner=' + str(runner) + '\n'
                                      + '24 jobs; max idle agent pool=24; timeoutFactor=1; two-hour total cap\n')
    print(f'24 test jobs; timeoutFactor=1; two-hour total cap. Results: {out}', flush=True)
    print('Each VM defaults to 2 GiB ergonomic RAM / 8 processors; explicit test flags override.', flush=True)
    deadline = time.monotonic() + 7200
    common = [str(runner), '-Xms64m', '-Xmx512m', '-jar', str(jtreg / 'lib/jtreg.jar'),
               f'-jdk:{jdk}', '-agentvm', '-conc:24', '--max-pool-size=24', '-timeoutFactor:1',
               '-e:JAVA_TOOL_OPTIONS',
               '-retain:fail,error', '-verbose:summary',
               f'-nativepath:{build}/images/test/hotspot/jtreg/native']
    print('Verifying limits inside a jtreg test VM and its child...', flush=True)
    preflight = common + [f'-w:{out}/preflight/work', f'-r:{out}/preflight/report',
                          str(root / 'tests/tier1-environment')]
    rc, _ = run_live(preflight, env, out / 'preflight.log', min(deadline, time.monotonic() + 120))
    if rc:
        (out / 'results.txt').write_text(f'preflight exit={rc}\nmain batch not started\n')
        print(f'Environment preflight failed (exit={rc}); refusing the main batch. See {out}/preflight.log', flush=True)
        return rc
    command = common + [f'-w:{out}/work', f'-r:{out}/report']
    print('Enumerating selected tests (up to two minutes)...', flush=True)
    rc, _ = run_live(command + ['-listtests'] + tests, env, out / 'list.log', min(deadline, time.monotonic() + 120))
    if rc:
        print(f'Test enumeration failed: exit={rc}', flush=True)
        return rc
    text = (out / 'list.log').read_text(errors='replace')
    match = re.search(r'Tests found:\s*([\d,]+)', text)
    count = int(match.group(1).replace(",", "")) if match else len(re.findall(r'^\s*\S+\.(?:java|sh)(?:#[^\s]+)?\s*$', text, re.M))
    if not count:
        print('No tests enumerated; refusing an empty run.', flush=True)
        return 1
    env['JDK25_SELECTED_COUNT'] = str(count)
    env['JDK25_RESOURCE_HISTORY'] = str(out / 'resource-history.log')
    print(f'Running {count} selected cases; heartbeat every 10 seconds. Log: {out}/run.log', flush=True)
    rc, counts = run_live(command + tests, env, out / 'run.log', deadline, True)
    (out / 'results.txt').write_text(f'jtreg/timeout exit={rc}\nreported statuses={dict(counts)}\n')
    print(f'jtreg/timeout exit={rc}\nResults: {out}', flush=True)
    if rc:
        print('Collect diagnostics: python3 tests/collect-hotspot-tier1-evidence.py ' + str(out), flush=True)
    return rc


if __name__ == '__main__':
    sys.exit(main())
