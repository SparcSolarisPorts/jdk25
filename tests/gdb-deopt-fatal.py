"""Capture fatal function entries without signal catchpoints on Solaris."""
import os
import gdb

out = os.environ['JDK25_GDB_OUT']
count = 0

def capture_deopt_fatal():
    global count
    count += 1
    # Several report_and_die overloads may be entered for one fatal error.
    if count > 4:
        return
    sections = ['Fatal function entry %d' % count]
    for command in ('info program', 'bt 40', 'info args', 'info registers',
                    'thread apply all bt 16', 'x/12i $pc-16'):
        try:
            sections.append('=== %s ===\n%s' % (command, gdb.execute(command, to_string=True)))
        except gdb.error as error:
            sections.append('%s: %s' % (command, error))
    with open(os.path.join(out, 'fatal-entry-%d.log' % count), 'w') as stream:
        stream.write('\n'.join(sections))

def record_exit(event):
    with open(os.path.join(out, 'inferior-exit.txt'), 'w') as stream:
        stream.write('inferior exit_code=%s\nfatal function entries=%d\n' %
                     (getattr(event, 'exit_code', None), count))

gdb.events.exited.connect(record_exit)
for signal in ('SIGPIPE', 'SIGUSR1', 'SIGUSR2', 'SIGLWP', 'SIGWAITING', 'SIGCANCEL', 'SIGJVM'):
    try:
        gdb.execute('handle %s nostop noprint pass' % signal, to_string=True)
    except gdb.error:
        pass
