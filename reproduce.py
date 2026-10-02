"""Reproduce each bounded suite with one child at a time; compare exact CSV evidence.

Usage: python reproduce.py --output /a/new/directory
The directory must not exist. Platform timing and RSS need not equal stored values.
"""
from __future__ import annotations
import argparse,csv,json,subprocess,sys,time,resource
from pathlib import Path

from speculation.validate import resource_guard

ROOT=Path(__file__).resolve().parent
SUITES=('relations','padding','circuits','general','gaps','baselines','negatives')

def read_rows(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();resource_guard();out=args.output.resolve()
    if out.exists():p.error('output must be a new directory')
    out.mkdir(parents=True)
    started=time.perf_counter();checks=[]
    unit=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],
                        cwd=ROOT,capture_output=True,text=True,timeout=40)
    (out/'unit-tests.txt').write_text(unit.stdout+unit.stderr)
    if unit.returncode:raise RuntimeError('unit tests failed')
    for suite in SUITES:
        command=[sys.executable,'-m','speculation.validate',suite,'--output',str(out)]
        child=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=40)
        if child.returncode:
            (out/(suite+'-failure.txt')).write_text(child.stdout+child.stderr)
            raise RuntimeError('suite failed: '+suite)
        expected=ROOT/'results'/'validation'
        if read_rows(out/(suite+'.csv'))!=read_rows(expected/(suite+'.csv')):
            raise AssertionError('exact result CSV mismatch: '+suite)
        measured=json.loads((out/(suite+'.json')).read_text())
        original=json.loads((expected/(suite+'.json')).read_text())
        if measured['counts']!=original['counts']:
            raise AssertionError('count mismatch: '+suite)
        checks.append(dict(suite=suite,exact_result_match=True,counts=measured['counts']))
    summary=dict(status='clean reproduction checks passed',suites=checks,
                 validation_cpu_seconds=sum(json.loads((out/(s+'.json')).read_text())['cpu_seconds'] for s in SUITES),
                 child_cpu_seconds=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+
                                   resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime,
                 wall_seconds=time.perf_counter()-started,
                 peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                 workers=1,
                 caveat='Self-reproduction of finite evidence, not an independent review or general proof')
    (out/'reproduction.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
