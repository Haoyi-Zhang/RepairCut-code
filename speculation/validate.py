"""Bounded deterministic checks. Counts are finite model checks, not workloads or proofs."""
from __future__ import annotations
import argparse
import copy
import csv
import itertools
import json
import os
from pathlib import Path
import random
import resource
import time
from fractions import Fraction

from .model import Graph, Node, ARITY, load_graph
from .builders import (reduction, monotone_reduction, relation_truth, gap_graph,
                       full_observer, fullstate_cnf, correlated_components,
                       circuit_reduction, invalidation_gap_graph)
from .bitcheck import analyze
from .replay import run, fullstate_costs, certificate, verify
from .baselines import descendant_invalidation, complete_state_mismatch

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def resource_guard():
    if hasattr(os, 'sched_getaffinity'):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    limit = 3 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    resource.setrlimit(resource.RLIMIT_CPU, (35, 35))


def selected(g, mask):
    return {name for j, name in enumerate(g.speculative) if mask >> j & 1}


def relations():
    records, checks, replay_rows, lattice_edges = [], 0, 0, 0
    for q, m in ((1, 1), (1, 2), (2, 1)):
        for table in range(1 << (1 << (q+m))):
            oracle = relation_truth(table, q, m)
            for family, constructor in (('exclusive-pair', reduction),
                                        ('monotone-dual-rail', monotone_reduction)):
                g = constructor(q, m, table)
                a = analyze(g)
                require((a.adaptive_min <= m) == oracle['adaptive'], 'adaptive relation mismatch')
                require((a.uniform_min <= m) == oracle['uniform'], 'uniform relation mismatch')
                for u, exists in enumerate(oracle['pointwise']):
                    require((a.pointwise_min[1+2*u] <= m) == exists, 'pointwise relation mismatch')
                    require(a.pointwise_min[2*u] == 0, 'd=0 should cost zero')
                if q == m == 1:
                    for mask in range(1 << a.p):
                        for i, e in enumerate(g.environments()):
                            good = run(g, e, selected(g, mask))[0] == run(g, e, None)[0]
                            require(bool(a.good_environments(mask) >> i & 1) == good,
                                    'independent replay disagrees')
                            replay_rows += 1
                if family == 'monotone-dual-rail':
                    for mask in range(1 << a.p):
                        for j in range(a.p):
                            if not mask >> j & 1:
                                subset = a.good_environments(mask)
                                superset = a.good_environments(mask | 1 << j)
                                require(subset & ~superset == 0, 'monotonicity failure')
                                lattice_edges += 1 << a.q
                records.append(dict(family=family,q=q,m=m,table=table,
                                    nodes=len(g.nodes),prefix=a.p,rows=a.rows,
                                    adaptive=a.adaptive_min,uniform=a.uniform_min,
                                    oracle_adaptive=int(oracle['adaptive']),
                                    oracle_uniform=int(oracle['uniform'])))
                checks += 1
    return records, dict(graph_instances=checks, independent_replay_rows=replay_rows,
                         monotonicity_environment_edges=lattice_edges)


def padding():
    pool = [[(j, c == 1) for j, c in enumerate(choices) if c]
            for choices in itertools.product((-1, 0, 1), repeat=2) if any(choices)]
    records, repaired_rows = [], 0
    for mask in range(1, 1 << len(pool)):
        clauses = [c for j, c in enumerate(pool) if mask >> j & 1]
        sat = any(all(any(bool(u >> j & 1) == sign for j, sign in c) for c in clauses)
                  for u in range(4))
        for mode in ('adaptive', 'uniform'):
            g, k, meta = fullstate_cnf(2, clauses, mode)
            costs, masks, union = fullstate_costs(g)
            value = max(costs) if mode == 'adaptive' else len(union)
            require((value <= k) == (not sat), 'UNSAT padding mismatch')
            for e, repair in zip(g.environments(), masks):
                require(run(g, e, repair)[0] == run(g, e, None)[0], 'mismatch repair failed')
                repaired_rows += 1
            records.append(dict(cnf_mask=mask,mode=mode,satisfiable=int(sat),
                                prefix=len(g.speculative),budget=k,cost=value,**meta))
    return records, dict(graph_instances=len(records), repaired_environment_rows=repaired_rows)


def random_formula(rng, q, m, count=12):
    names = [f'v{i}' for i in range(q+m)]
    inputs = tuple(names)
    nodes = []
    ops = tuple(ARITY)
    for i in range(count):
        op = rng.choice(ops)
        args = tuple(rng.choice(names) for _ in range(ARITY[op]))
        name = f'n{i}'
        nodes.append(Node(name, op, args, False)); names.append(name)
    g = Graph(inputs, ((0, 1),)*len(inputs), (0,)*len(inputs), tuple(nodes), (names[-1],))
    return load_graph(g.to_dict())


def circuits():
    rng = random.Random(1729)
    records, replay_rows = [], 0
    for index in range(128):
        q, m = ((1, 2), (2, 1))[index % 2]
        formula = random_formula(rng, q, m)
        table = 0
        for j, e in enumerate(formula.environments()):
            table |= run(formula, e, None)[0][0] << j
        oracle = relation_truth(table, q, m)
        g = circuit_reduction(formula, q, m)
        a = analyze(g)
        require((a.adaptive_min <= m) == oracle['adaptive'], 'circuit adaptive mismatch')
        require((a.uniform_min <= m) == oracle['uniform'], 'circuit uniform mismatch')
        # A positive/negative rail is created at most six times per source gate.
        require(len(g.nodes) <= (3*m+1)+q+6*len(formula.nodes)+2*m+1,
                'linear construction size bound failed')
        for i, e in enumerate(g.environments()):
            for mask in range(1 << a.p):
                good = run(g, e, selected(g, mask))[0] == run(g, e, None)[0]
                require(bool(a.good_environments(mask) >> i & 1) == good, 'circuit replay mismatch')
                replay_rows += 1
        records.append(dict(case=index,q=q,m=m,formula_gates=len(formula.nodes),
                            constructed_gates=len(g.nodes),truth_table=table,
                            rows=a.rows,adaptive=a.adaptive_min,uniform=a.uniform_min))
    return records, dict(graph_instances=len(records),independent_replay_rows=replay_rows,seed=1729)


def general():
    rng = random.Random(65537)
    records, checks = [], 0
    for index in range(128):
        g0 = random_formula(rng, 1, 2, count=9)
        g = Graph(g0.inputs, g0.domains,
                  tuple(rng.randrange(2) for _ in g0.inputs),
                  tuple(Node(n.name,n.op,n.args,i<4) for i,n in enumerate(g0.nodes)),
                  (g0.nodes[-1].name,))
        for observer, observed in (('terminal', g), ('complete-state', full_observer(g))):
            a = analyze(observed)
            cs, ms, union = fullstate_costs(observed)
            if observer == 'complete-state':
                require(a.pointwise_min == cs and a.uniform_min == len(union),
                        'complete-state costs mismatch')
            for mask in range(1 << a.p):
                repair = selected(observed, mask)
                for i, e in enumerate(observed.environments()):
                    good = run(observed,e,repair)[0] == run(observed,e,None)[0]
                    require(bool(a.good_environments(mask) >> i & 1) == good, 'general replay mismatch')
                    if observer == 'complete-state':
                        require(good == (ms[i] <= repair), 'unique least repair mismatch')
                    checks += 1
            require(verify(observed, certificate(observed,a.adaptive_min,'adaptive',a.pointwise_mask)),
                    'adaptive certificate rejected')
            require(verify(observed, certificate(observed,a.uniform_min,'uniform',[a.uniform_mask])),
                    'uniform certificate rejected')
            records.append(dict(case=index,observer=observer,q=a.q,p=a.p,rows=a.rows,
                                adaptive=a.adaptive_min,uniform=a.uniform_min))
    return records, dict(graph_instances=len(records),independent_replay_rows=checks,seed=65537)


def gaps():
    records=[]
    family_pairs = 0
    unit_vectors = 0
    uniform_intersections = 0
    for m in range(1, 9):
        g = gap_graph(m); a=analyze(g)
        require(a.adaptive_min == 1 and a.uniform_min == m,'tight gap failed')
        environments = list(g.environments())
        full_environment_bits = (1 << len(environments)) - 1
        uniform_masks = []
        for mask in range(1 << a.p):
            if a.good_environments(mask) == full_environment_bits:
                uniform_masks.append(mask)
            if m <= 3:
                repair = selected(g, mask)
                for row, environment in enumerate(environments):
                    active = {f's{i}' for i in range(m) if environment[f'u{i}'] == 1}
                    expected = (environment['d'] == 0 or not active or bool(repair & active))
                    enumerated = bool(a.good_environments(mask) >> row & 1)
                    replayed = run(g, environment, repair)[0] == run(g, environment, None)[0]
                    require(enumerated == expected == replayed,
                            'gap success-family characterization failed')
                    family_pairs += 1
        require(uniform_masks == [(1 << m) - 1],
                'full-domain uniform family is not the singleton full repair')
        uniform_intersections += 1
        for active_index in range(m):
            environment = {'d': 1, **{f'u{i}': int(i == active_index) for i in range(m)}}
            row = environments.index(environment)
            successful = [mask for mask in range(1 << a.p)
                          if a.good_environments(mask) >> row & 1]
            require(successful and all(mask >> active_index & 1 for mask in successful),
                    'unit-vector environment does not force its active slot')
            require((1 << active_index) in successful,
                    'unit-vector environment lacks a one-slot adaptive repair')
            unit_vectors += 1
        records.append(dict(prefix=m,uncertain_inputs=a.q,rows=a.rows,
                            adaptive=a.adaptive_min,uniform=a.uniform_min))
    g=correlated_components(); a=analyze(g)
    require(a.adaptive_min==1 and a.uniform_min==2,'correlated composition failed')
    singles=[]
    for o in g.observations:
        obj=g.to_dict(); obj['observations']=[o]
        singles.append(analyze(load_graph(obj)).adaptive_min)
    require(singles==[1,1], 'component scalar maximum failed')
    require(family_pairs == 168, 'p=1,2,3 success-family coverage changed')
    require(unit_vectors == 36, 'unit-vector coverage changed')
    require(uniform_intersections == 8, 'uniform-intersection coverage changed')
    return records,dict(gap_instances=8,correlated_composition=dict(joint_adaptive=1,
                            separate_adaptive_sum=sum(singles),joint_uniform=2))


def baselines():
    records=[]
    sound_rows=0
    refinement_rows=0
    for p in range(1, 13):
        g=invalidation_gap_graph(p)
        complete=full_observer(g)
        a=analyze(complete)
        for i,e in enumerate(complete.environments()):
            reach=descendant_invalidation(complete,e)
            mismatch=complete_state_mismatch(complete,e)
            require(run(complete,e,reach)[0] == run(complete,e,None)[0],
                    'descendant invalidation was not safe')
            require(mismatch <= reach, 'mismatch escaped syntactic invalidation')
            require(len(mismatch) == a.pointwise_min[i], 'mismatch optimum disagrees')
            sound_rows += 1
            if e['d']==1:
                require(len(reach)==p and len(mismatch)==1,
                        'tight invalidation gap family failed')
                ratio=float(Fraction(len(reach), len(mismatch)))
            else:
                ratio='undefined'
            records.append(dict(family='tight-invalidation',case=p,environment_d=e['d'],
                                prefix=p,syntactic_cost=len(reach),optimal_cost=len(mismatch),
                                ratio_when_positive=ratio))

    rng=random.Random(104729)
    random_pairs=[]
    for index in range(128):
        g0=random_formula(rng,1,2,count=9)
        terminal=Graph(g0.inputs,g0.domains,
                       tuple(rng.randrange(2) for _ in g0.inputs),
                       tuple(Node(n.name,n.op,n.args,i<4) for i,n in enumerate(g0.nodes)),
                       (g0.nodes[-1].name,))
        strong=full_observer(terminal)
        weak_result=analyze(terminal)
        strong_result=analyze(strong)
        require(strong_result.adaptive_min >= weak_result.adaptive_min,
                'adaptive cost fell under observation refinement')
        require(strong_result.uniform_min >= weak_result.uniform_min,
                'uniform cost fell under observation refinement')
        for i,e in enumerate(terminal.environments()):
            require(strong_result.pointwise_min[i] >= weak_result.pointwise_min[i],
                    'pointwise cost fell under observation refinement')
            repair=descendant_invalidation(terminal,e)
            require(run(terminal,e,repair)[0] == run(terminal,e,None)[0],
                    'random descendant invalidation was not safe')
            require(run(strong,e,repair)[0] == run(strong,e,None)[0],
                    'random complete-state invalidation was not safe')
            require(complete_state_mismatch(strong,e) <= repair,
                    'random mismatch escaped invalidation')
            sound_rows += 2
            refinement_rows += 1
        syntactic_cost=max(len(descendant_invalidation(terminal,e))
                           for e in terminal.environments())
        optimal_cost=strong_result.adaptive_min
        ratio=(float(Fraction(syntactic_cost, optimal_cost))
               if optimal_cost > 0 else 'undefined')
        if optimal_cost > 0:
            require(ratio == syntactic_cost / optimal_cost,
                    'positive-denominator ratio does not match the two cost columns')
        else:
            require(ratio == 'undefined',
                    'zero-denominator ratio must be explicitly undefined')
        random_pairs.append((syntactic_cost, optimal_cost))
        records.append(dict(family='random-refinement',case=index,environment_d=-1,
                            prefix=len(terminal.speculative),
                            syntactic_cost=syntactic_cost,
                            optimal_cost=optimal_cost,
                            ratio_when_positive=ratio))

    expected_frequency = (
        (5, 0, 0, 0, 0),
        (0, 20, 0, 0, 0),
        (2, 10, 17, 0, 0),
        (1, 3, 17, 21, 0),
        (0, 1, 3, 16, 12),
    )
    frequency = tuple(tuple(sum((s, o) == (syntactic, optimal)
                                    for s, o in random_pairs)
                              for optimal in range(5))
                      for syntactic in range(5))
    positive_ratios = [Fraction(s, o) for s, o in random_pairs if o > 0]
    mean_ratio = sum(positive_ratios, Fraction(0, 1)) / len(positive_ratios)
    require(len(random_pairs) == 128, 'random baseline case count changed')
    require(sum(s > o for s, o in random_pairs) == 53,
            'random baseline strict-gap count changed')
    require(sum(s == o for s, o in random_pairs) == 75,
            'random baseline equality count changed')
    require(len(positive_ratios) == 120,
            'random baseline positive-optimum count changed')
    require(max(positive_ratios) == 4,
            'random baseline maximum ratio changed')
    require(mean_ratio == Fraction(187, 144),
            'random baseline mean ratio changed')
    require(frequency == expected_frequency,
            'random baseline cost-pair frequency table changed')

    return records,dict(tight_instances=12,random_graphs=128,
                        descendant_soundness_rows=sound_rows,
                        observation_refinement_environment_rows=refinement_rows,seed=104729)


def negatives():
    records=[]
    def expect_error(name, f):
        try: f()
        except ValueError:
            records.append(dict(case=name,rejected=1)); return
        raise AssertionError('negative control accepted: '+name)
    g=gap_graph(2); a=analyze(g)
    cert=certificate(g,1,'adaptive',a.pointwise_mask)
    mutations={
        'missing_environment': lambda x: x['rows'].pop(),
        'duplicate_environment': lambda x: x['rows'].__setitem__(1,copy.deepcopy(x['rows'][0])),
        'false_uniform_mode': lambda x: x.__setitem__('mode','uniform'),
        'too_small_budget': lambda x: x.__setitem__('budget',0),
        'invalid_budget_type': lambda x: x.__setitem__('budget',True),
        'wrong_cache': lambda x: x['rows'][0]['cache'].__setitem__('s0',1),
        'wrong_trace': lambda x: x['rows'][0]['trace'].__setitem__('s0',1),
        'wrong_output': lambda x: x['rows'][0].__setitem__('output',[1]),
        'bool_output': lambda x: x['rows'][0].__setitem__('output',[False]),
        'unknown_repair': lambda x: x['rows'][0].__setitem__('selected',['not-a-node']),
        'duplicate_repair': lambda x: x['rows'][0].__setitem__('selected',['s0','s0']),
        'bad_map_type': lambda x: x['rows'][0].__setitem__('cache',[]),
    }
    for name, f in mutations.items():
        obj=copy.deepcopy(cert); f(obj)
        expect_error(name,lambda obj=obj:verify(g,obj))
    obj=g.to_dict(); obj['dependencies'].pop()
    expect_error('missing_dependency',lambda:load_graph(obj))
    obj=g.to_dict(); obj['dependencies'].append(['d','s0'])
    expect_error('duplicate_dependency',lambda:load_graph(obj))
    for name, mutate in [
        ('effectful_node',lambda x:x['nodes'][0].__setitem__('op','network-send')),
        ('unhashable_operation',lambda x:x['nodes'][0].__setitem__('op',[])),
        ('unhashable_observation',lambda x:x.__setitem__('observations',[{}])),
        ('malformed_input',lambda x:x['inputs'].__setitem__(0,0)),
        ('malformed_node',lambda x:x['nodes'].__setitem__(0,None)),
        ('cycle_or_forward_edge',lambda x:x['nodes'][0].__setitem__('args',['s0'])),
        ('nonprefix_speculation',lambda x:x['nodes'][-1].__setitem__('speculative',True)),
    ]:
        obj=g.to_dict();mutate(obj)
        expect_error(name,lambda obj=obj:load_graph(obj))
    # Scientific mutants are expected to run, but disagree with the proved criterion.
    good=analyze(monotone_reduction(1,2,0))
    bad=analyze(monotone_reduction(1,2,0,escape_length=2))
    require(good.adaptive_min==3 and bad.adaptive_min==2,'escape mutant not detected')
    records.append(dict(case='short_escape_changes_false_to_true',rejected=1))
    g=reduction(1,1,9); a=analyze(g)
    require(a.adaptive_min==1 and a.uniform_min==2,'quantifier mutant not detected')
    union=0
    for mask in a.pointwise_mask: union |= mask
    require(a.good_environments(union) != (1 << (1 << a.q))-1,
            'union of adaptive repairs unexpectedly safe')
    records.extend([dict(case='swapped_quantifiers',rejected=1),
                    dict(case='union_of_adaptive_repairs',rejected=1)])
    return records,dict(negative_controls=len(records),detected=len(records))


SUITES={'relations':relations,'padding':padding,'circuits':circuits,
        'general':general,'gaps':gaps,'baselines':baselines,'negatives':negatives}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('suite',choices=SUITES)
    parser.add_argument('--output',type=Path,required=True,
                        help='A new directory; existing result files are never overwritten')
    args=parser.parse_args()
    resource_guard()
    args.output.mkdir(parents=True,exist_ok=True)
    jp=args.output/(args.suite+'.json'); cp=args.output/(args.suite+'.csv')
    if jp.exists() or cp.exists():
        parser.error('result path already exists; use a fresh output directory')
    wall=time.perf_counter(); cpu=time.process_time()
    records,counts=SUITES[args.suite]()
    result=dict(suite=args.suite,status='finite checks passed',counts=counts,
                cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall,
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                workers=1,failures=0,timeouts=0,
                interpretation='Bounded finite validation; not a general machine proof or representative workload study')
    with cp.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    with jp.open('x') as f: json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
