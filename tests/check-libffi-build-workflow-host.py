#!/usr/bin/env python3
"""Run the real dependency script with mocked external commands.
Validate the stage boundaries that failed on Solaris, not libffi itself."""
from pathlib import Path
import io, os, subprocess, tarfile, tempfile
root=Path(__file__).resolve().parents[1]
script=root/'tests/build-libffi-v86.sh'
with tempfile.TemporaryDirectory() as tmp:
    base=Path(tmp);bin=base/'bin';bin.mkdir()
    def tool(name, text):
        p=bin/name;p.write_text('#!/usr/bin/env bash\n'+text);p.chmod(0o755)
    configure='''echo "configure MAKE=$MAKE CFLAGS=$CFLAGS LDFLAGS=$LDFLAGS $*" >> "$TRACE"
[[ "$MAKE" == gmake && "$CFLAGS" == '-m64 -O2' && "$LDFLAGS" == -m64 ]] || exit 31
[[ " $* " == *' --disable-dependency-tracking '* ]] || exit 32
exit "${CONFIG_RC:-0}"
'''
    archive=base/'source.tar.gz'
    with tarfile.open(archive,'w:gz') as t:
        for name,data in [('configure',configure),('LICENSE','mock license\n')]:
            data=data.encode();info=tarfile.TarInfo('libffi-3.4.8/'+name);info.size=len(data);t.addfile(info,io.BytesIO(data))
    tool('uname','case "$1" in -s) echo SunOS;; -p) echo sparc;; esac\n')
    tool('curl','while (($#)); do if [[ "$1" == --output ]]; then cp "$MOCK_ARCHIVE" "$2"; exit $?; fi; shift; done; exit 3\n')
    tool('digest','if [[ ${BAD_SHA:-0} == 1 ]]; then echo bad; else echo bc9842a18898bfacb0ed1252c4febcc7e78fa139fd27fdc7a3e30d9d9356119b; fi\n')
    tool('gmake','''echo "gmake $*" >> "$TRACE"
if [[ ${1:-} == install ]]; then
  [[ ${INSTALL_RC:-0} == 0 ]] || exit "$INSTALL_RC"
  mkdir -p "$LIBFFI_HOME/include" "$LIBFFI_HOME/lib"
  touch "$LIBFFI_HOME/include/ffi.h" "$LIBFFI_HOME/lib/libffi.so.8"
else exit "${BUILD_RC:-0}"; fi
''')
    for mode,rc,extra in [('ok',0,{}),('configure',7,{'CONFIG_RC':'7'}),('build',8,{'BUILD_RC':'8'}),('install',9,{'INSTALL_RC':'9'}),('checksum',1,{'BAD_SHA':'1'})]:
        work=base/mode;work.mkdir();trace=work/'trace';prefix=work/'ffi prefix'
        env=dict(os.environ,PATH=str(bin)+':'+os.environ['PATH'],TMPDIR=str(work),LIBFFI_HOME=str(prefix),MOCK_ARCHIVE=str(archive),TRACE=str(trace),**extra)
        result=subprocess.run(['bash',str(script)],env=env,text=True,capture_output=True)
        assert result.returncode==rc,(mode,result.returncode,result.stdout,result.stderr)
        steps=trace.read_text() if trace.exists() else ''
        if mode=='ok':
            assert 'gmake install' in steps and (prefix/'LICENSE.libffi').exists()
            assert 'Installed libffi:' in result.stdout
        else:
            assert 'Installed libffi:' not in result.stdout
            assert not (prefix/'LICENSE.libffi').exists()
        if mode=='configure': assert 'gmake' not in steps.split('\n',1)[-1]
        if mode=='build': assert 'gmake install' not in steps
        if mode=='checksum': assert not steps
    print('PASS: libffi setup success and configure/build/install/checksum failure boundaries; GNU make and LP64 flags')
