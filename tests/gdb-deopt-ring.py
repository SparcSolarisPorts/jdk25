"""GDB Python: retain the last eight signal stops without suppressing signals."""
import collections
import os
import gdb

out = os.environ['JDK25_GDB_OUT']
ring = collections.deque(maxlen=8)
count = 0

def capture_deopt_signal():
    global count
    count += 1
    sections = ['Signal stop %d' % count]
    for command in ('info program', 'p $_siginfo', 'info symbol $pc',
                    'bt 24', 'info registers', 'x/12i $pc-16',
                    'x/24gx $sp+2047'):
        try:
            sections.append('=== %s ===\n%s' % (command, gdb.execute(command, to_string=True)))
        except gdb.error as error:
            sections.append('%s: %s' % (command, error))
    ring.append('\n'.join(sections))
    with open(os.path.join(out, 'signal-captures.log'), 'w') as stream:
        stream.write('\n\n'.join(ring))
        stream.flush()

def record_exit(event):
    with open(os.path.join(out, 'inferior-exit.txt'), 'w') as stream:
        stream.write('inferior exit_code=%s\nsignal stops=%d\n' %
                     (getattr(event, 'exit_code', None), count))

gdb.events.exited.connect(record_exit)
for signal in ('SIGPIPE', 'SIGUSR1', 'SIGUSR2', 'SIGLWP', 'SIGWAITING', 'SIGCANCEL', 'SIGJVM'):
    try:
        gdb.execute('handle %s nostop noprint pass' % signal, to_string=True)
    except gdb.error:
        pass
