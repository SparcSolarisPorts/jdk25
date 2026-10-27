#!/usr/bin/env python3
"""Bounded text-only evidence from an existing jtreg run; never read cores."""
import csv, io, json, os, re, resource, subprocess, sys, time, zipfile
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

root=Path.cwd()
if len(sys.argv)>1:
    out=Path(sys.argv[1]).resolve()
else:
    runs=sorted(root.glob('hotspot-tier1-*'),key=lambda p:p.stat().st_mtime,reverse=True)
    runs=[p for p in runs if p.is_dir() and ((p/'work').is_dir() or (p/'preflight/work').is_dir())]
    if not runs: sys.exit('No hotspot-tier1 run found; pass its directory.')
    out=runs[0].resolve()
if not (out/'work').is_dir() and not (out/'preflight/work').is_dir():sys.exit('Missing work directory: '+str(out))
archive=out/'tier1-text-evidence.zip'
since=((out/'list.log').stat().st_mtime-600 if (out/'list.log').exists() else out.stat().st_mtime-10800)
LIMIT=48*1024*1024
used=0; omitted=[]; clipped=[]

def read_bounded(path,limit=192*1024):
    size=path.stat().st_size
    with path.open('rb') as f:
        if size<=limit:return f.read()
        first=limit//2; data=f.read(first);f.seek(-first,2);tail=f.read(first)
    clipped.append(str(path))
    return data+b'\n\n[COLLECTOR: MIDDLE OMITTED; ORIGINAL SIZE '+str(size).encode()+b' BYTES]\n\n'+tail

def command(argv,seconds=12):
    try:
        p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=seconds, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
        return ('$ '+' '.join(argv)+'\nexit='+str(p.returncode)+'\n').encode()+p.stdout[:256*1024]
    except (OSError,subprocess.TimeoutExpired) as e:return (str(argv)+'\n'+str(e)+'\n').encode()

# Logs can have carriage-return progress bars mixed into their status lines.
log=out/'run.log'
console=read_bounded(log,2*1024*1024).decode(errors='replace') if log.exists() else ''
reported=re.findall(r'(?:^|\n|\r)(Passed:|FAILED:|Error:)\s+(\S+\.(?:java|sh)(?:#[^\s]+)?)',console)
reported_bad={name for status,name in reported if status!='Passed:'}
counts=Counter(status for status,name in reported)
print('Collecting existing results:',out,flush=True)

with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    def add(name,data):
        global used
        if isinstance(data,str):data=data.encode()
        if used+len(data)>LIMIT:omitted.append(name);return
        used+=len(data);z.writestr(name,data)
    def add_file(name,path,limit=192*1024):
        try:
            if path.is_file() and not path.is_symlink():add(name,read_bounded(path,limit))
        except OSError as e:omitted.append(str(path)+': '+str(e))
    add_file('run.log',log,2*1024*1024)
    add_file('list.log',out/'list.log',512*1024)
    add_file('preflight.log',out/'preflight.log',192*1024)
    for p in (out/'preflight/work').rglob('*.jtr'):
        add_file('preflight/'+str(p.relative_to(out/'preflight/work')),p)
    add_file('resource-history.log',out/'resource-history.log',512*1024)
    add_file('run-environment.txt',out/'environment.txt',64*1024)
    add_file('results.txt',out/'results.txt',64*1024)
    add_file('build-tail.log',Path('/tmp/jdk25-build.log'),96*1024)
    add('reported-failed-tests.txt',''.join('test/hotspot/jtreg/'+p+'\n' for p in sorted(reported_bad)))
    records=[]; selected=[]
    for p in (out/'work').rglob('*.jtr'):
        if p.is_symlink():continue
        try:
            with p.open('rb') as f:header=f.read(32768).decode(errors='replace')
            match=re.search(r'^execStatus=(.*)$',header,re.M)
            status=match.group(1).strip() if match else 'No final execStatus in header'
            test=re.search(r'^test=(.*)$',header,re.M)
            test=test.group(1).strip() if test else str(p.relative_to(out/'work'))
            records.append((test,status,str(p.relative_to(out))))
            if not status.startswith('Passed.'):
                selected.append((test not in reported_bad,p))
        except OSError as e:omitted.append(str(e))
    for _,p in sorted(selected,key=lambda x:(x[0],str(x[1]))):
        add_file('jtr/'+str(p.relative_to(out/'work')),p)
    stream=io.StringIO();w=csv.writer(stream);w.writerow(['test','execStatus','file']);w.writerows(sorted(records));add('jtr-status.csv',stream.getvalue())
    # Retained native gtest XML contains the assertion omitted by wrapper output.
    for p in (out/'work').rglob('test_result.xml'):
        try:
            if p.is_symlink() or p.stat().st_size>8*1024*1024:continue
            tree=ET.parse(p)
            failures=[c for c in tree.iter('testcase') if c.find('failure') is not None or c.find('error') is not None]
            if failures:
                data=b'\n'.join(ET.tostring(c,encoding='utf-8') for c in failures)
                add('gtest-failures/'+str(p.relative_to(out/'work')),data)
        except (OSError,ET.ParseError) as e:omitted.append(str(e))
    # Include harness crash reports outside work as well as retained child reports.
    fatal=set((out/'work').rglob('hs_err*.log'))
    for parent in (root,root/'make',Path('/tmp')):
        try:
            fatal.update(p for p in parent.glob('hs_err*.log') if p.stat().st_mtime>=since)
        except OSError:pass
    fatal_index=[]
    def mtime_or_zero(p):
        try:return p.stat().st_mtime
        except OSError:return 0
    for i,p in enumerate(sorted(fatal,key=mtime_or_zero,reverse=True)):
        if i>=160:omitted.append('Additional crash report: '+str(p));continue
        add_file('crashes/%03d-%s'%(i,p.name),p,256*1024)
        try:
            with p.open('rb') as f:h=f.read(16384).decode(errors='replace')
            version=re.search(r'^# JRE version: (.*)',h,re.M)
            frame=re.search(r'^# Problematic frame:\n# (.*)',h,re.M)
            fatal_index.append({'path':str(p),'JRE':version.group(1) if version else '', 'frame':frame.group(1) if frame else ''})
        except OSError:pass
    add('crash-index.json',json.dumps(fatal_index,indent=2))
    commands=[['uname','-a'],['isainfo','-b'],['/usr/bin/sh','-c','/usr/sbin/swap -s'],['/usr/bin/sh','-c','/usr/sbin/swap -l'],['df','-h','/tmp'],
              ['ps','-eo','pid,ppid,nlwp,pcpu,vsz,rss,comm'],
              ['git','rev-parse','HEAD'],['git','status','--short'],
              ['/usr/jdk/jdk-21/bin/java','-version'],
              [str(root/'build/solaris-sparcv9-server-release/images/jdk/bin/java'),'-version']]
    for i,cmd in enumerate(commands):add('environment/%02d.txt'%i,command(cmd))
    limits={}
    for name in ('RLIMIT_AS','RLIMIT_NPROC','RLIMIT_NOFILE','RLIMIT_STACK','RLIMIT_CORE'):
        if hasattr(resource,name):limits[name]=resource.getrlimit(getattr(resource,name))
    add('environment/resource-limits.json',json.dumps(limits,indent=2))
    add_file('environment/spec.gmk',root/'build/solaris-sparcv9-server-release/spec.gmk',256*1024)
    z.writestr('collection-summary.json',json.dumps({'run':str(out),'reported_status_counts':dict(counts),
        'reported_unsuccessful':len(reported_bad),'jtr_files_seen':len(records),
        'nonpassed_jtr_selected':len(selected),'crash_reports_selected':len(fatal_index),
        'text_bytes_before_summary':used,'truncated_files':clipped,'omitted':omitted,
        'note':'Current resource readings are after the run, not measurements during the failure. Core files and heap dumps were never read.'},indent=2))
print('Reported:',dict(counts))
print('JTR records:',len(records),'nonpassed:',len(selected),'crash reports:',len(fatal_index))
print('Text bytes collected:',used,'archive bytes:',archive.stat().st_size)
print('Truncated files:',len(clipped),'omitted items:',len(omitted))
print('Send:',archive)
