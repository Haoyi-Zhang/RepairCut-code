"""Offline bounded exact checking of declared Boolean cache-repair graphs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .model import load_graph
from .bitcheck import analyze
from .replay import certificate, verify
from .validate import resource_guard

MAX_INPUT_BYTES = 16 * 1024**2

def read_json(path: Path):
    with path.open('rb') as f:
        payload=f.read(MAX_INPUT_BYTES+1)
    if len(payload)>MAX_INPUT_BYTES:
        raise ValueError('JSON input exceeds the 16 MiB admission bound')
    return json.loads(payload)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('analyze'); p.add_argument('graph',type=Path)
    p=commands.add_parser('certify'); p.add_argument('graph',type=Path)
    p.add_argument('--mode',choices=('adaptive','uniform'),required=True)
    p.add_argument('--output',type=Path,required=True)
    p=commands.add_parser('verify'); p.add_argument('graph',type=Path); p.add_argument('certificate',type=Path)
    args=parser.parse_args()
    resource_guard()
    try:
        g=load_graph(read_json(args.graph))
        if args.command=='verify':
            verify(g,read_json(args.certificate))
            print(json.dumps({'valid':True,'meaning':'Explicit domain coverage and replay; no optimality claim'}))
            return
        a=analyze(g)
        if args.command=='analyze':
            print(json.dumps({'uncertain_inputs':a.q,'prefix_nodes':a.p,'rows':a.rows,
                              'pointwise_costs':a.pointwise_min,'adaptive_cost':a.adaptive_min,
                              'uniform_cost':a.uniform_min},indent=2))
            return
        budget=a.adaptive_min if args.mode=='adaptive' else a.uniform_min
        masks=a.pointwise_mask if args.mode=='adaptive' else [a.uniform_mask]
        doc=certificate(g,budget,args.mode,masks)
        verify(g,doc)
        with args.output.open('x') as f:
            json.dump(doc,f,indent=2);f.write('\n')
        print(json.dumps({'certificate':str(args.output),'mode':args.mode,'budget':budget}))
    except (ValueError,OSError,MemoryError) as exc:
        print(f'{type(exc).__name__}: {exc}',file=sys.stderr)
        raise SystemExit(2)

if __name__=='__main__':main()
