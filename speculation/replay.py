"""Independent demand-driven Boolean semantics, not the bit evaluator's operation table.

Input schema checking is shared through Graph. Gate evaluation, caching, graph
traversal, and repair validation are implemented separately. This is not a
machine-checked proof or an independent scientific review.
"""
from __future__ import annotations
from .model import Graph


def run(graph: Graph, environment: dict[str, int], selected: set[str] | None):
    if set(environment) != set(graph.inputs):
        raise ValueError('environment keys do not match')
    if any(type(environment[k]) is not int or environment[k] not in ds
           for k, ds in zip(graph.inputs, graph.domains)):
        raise ValueError('environment is not admissible')
    if selected is not None and not selected <= set(graph.speculative):
        raise ValueError('unknown selected node')
    nodes = {n.name: n for n in graph.nodes}
    predicted = dict(zip(graph.inputs, graph.prediction))

    memo: dict[tuple[str, str], bool] = {}

    def evaluate(name: str, phase: str) -> bool:
        # Explicit dependency stack avoids Python recursion limits on deep chains.
        pending = [(name, phase)]
        while pending:
            key = pending[-1]
            if key in memo:
                pending.pop(); continue
            current, current_phase = key
            if current in environment:
                memo[key] = bool(predicted[current] if current_phase == 'old' else environment[current])
                pending.pop(); continue
            node = nodes[current]
            if current_phase == 'mixed' and node.speculative and current not in selected:
                oldkey = (current, 'old')
                if oldkey not in memo:
                    pending.append(oldkey); continue
                memo[key] = memo[oldkey]
                pending.pop(); continue
            missing = [(a, current_phase) for a in node.args if (a, current_phase) not in memo]
            if missing:
                pending.extend(reversed(missing)); continue
            args = [memo[(a, current_phase)] for a in node.args]
            if node.op == 'zero': value = False
            elif node.op == 'one': value = True
            elif node.op == 'copy': value = args[0]
            elif node.op == 'not': value = not args[0]
            elif node.op == 'and': value = all(args)
            elif node.op == 'or': value = any(args)
            elif node.op == 'xor': value = args[0] != args[1]
            else: raise ValueError('unsupported primitive')
            memo[key] = value
            pending.pop()
        return memo[(name, phase)]
    phase = 'reference' if selected is None else 'mixed'
    trace = {n.name: int(evaluate(n.name, phase)) for n in graph.nodes}
    output = [int(evaluate(o, phase)) for o in graph.observations]
    old = {k: int(evaluate(k, 'old')) for k in graph.speculative}
    return output, trace, old


def fullstate_costs(graph: Graph):
    """Direct mismatch-set characterization; no enumeration of repair subsets."""
    pointwise, masks, union = [], [], set()
    for environment in graph.environments():
        _, ref, old = run(graph, environment, None)
        mismatch = {k for k in graph.speculative if ref[k] != old[k]}
        pointwise.append(len(mismatch)); masks.append(mismatch)
        union |= mismatch
    return pointwise, masks, union


def certificate(graph: Graph, budget: int, mode: str, masks: list[int]):
    """Construct a transparent explicit certificate, with a row per environment."""
    if len(graph.uncertain) > 16:
        raise ValueError('explicit certificate domain exceeds 65536 environments')
    envs = list(graph.environments())
    if mode not in ('adaptive', 'uniform') or len(masks) != (1 if mode == 'uniform' else len(envs)):
        raise ValueError('invalid certificate request')
    rows = []
    for i, e in enumerate(envs):
        mask = masks[0] if mode == 'uniform' else masks[i]
        if type(mask) is not int or not 0 <= mask < (1 << len(graph.speculative)):
            raise ValueError('invalid mask')
        selected = {k for j, k in enumerate(graph.speculative) if (mask >> j) & 1}
        out, trace, old = run(graph, e, selected)
        rows.append({'environment': e, 'selected': sorted(selected),
                     'cache': old, 'trace': trace, 'output': out})
    return {'mode': mode, 'budget': budget, 'rows': rows}


def verify(graph: Graph, document: dict) -> bool:
    """Reject omissions, duplicates, trace/cache tampering, and invalid observations."""
    if not isinstance(document, dict) or set(document) != {'mode', 'budget', 'rows'}:
        raise ValueError('invalid certificate fields')
    mode, budget, rows = document['mode'], document['budget'], document['rows']
    if mode not in ('adaptive', 'uniform') or type(budget) is not int or not 0 <= budget <= len(graph.speculative):
        raise ValueError('invalid certificate policy or budget')
    if len(graph.uncertain) > 16:
        raise ValueError('explicit certificate domain exceeds 65536 environments')
    expected = list(graph.environments())
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise ValueError('certificate does not cover the environment domain')
    first = None
    for e, row in zip(expected, rows):
        if not isinstance(row, dict) or set(row) != {'environment', 'selected', 'cache', 'trace', 'output'}:
            raise ValueError('invalid row fields')
        for field in ('environment', 'cache', 'trace'):
            value = row[field]
            if (not isinstance(value, dict) or any(not isinstance(k, str) or type(v) is not int
                                                  or v not in (0, 1) for k, v in value.items())):
                raise ValueError('row values must be canonical Boolean maps')
        if (not isinstance(row['output'], list)
                or any(type(v) is not int or v not in (0, 1) for v in row['output'])):
            raise ValueError('output must be a canonical Boolean list')
        if row['environment'] != e:
            raise ValueError('environment ordering or coverage mismatch')
        selected_list = row['selected']
        if (not isinstance(selected_list, list) or any(not isinstance(x, str) for x in selected_list)
                or len(selected_list) != len(set(selected_list))):
            raise ValueError('invalid repair set encoding')
        selected = set(selected_list)
        if len(selected) > budget:
            raise ValueError('repair budget exceeded')
        if first is None: first = selected
        if mode == 'uniform' and selected != first:
            raise ValueError('uniform mask changes after revelation')
        out, trace, old = run(graph, e, selected)
        reference, _, _ = run(graph, e, None)
        if row['cache'] != old or row['trace'] != trace or row['output'] != out:
            raise ValueError('certificate trace is inconsistent with replay')
        if out != reference:
            raise ValueError('visible output differs from reference')
    return True
