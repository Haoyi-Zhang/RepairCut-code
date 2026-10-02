"""Finite buffered single-assignment circuits. No external effects or dynamic code."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

ARITY = {'zero': 0, 'one': 0, 'copy': 1, 'not': 1, 'and': 2, 'or': 2, 'xor': 2}

@dataclass(frozen=True)
class Node:
    name: str
    op: str
    args: tuple[str, ...]
    speculative: bool

@dataclass(frozen=True)
class Graph:
    inputs: tuple[str, ...]
    domains: tuple[tuple[int, ...], ...]
    prediction: tuple[int, ...]
    nodes: tuple[Node, ...]
    observations: tuple[str, ...]

    @property
    def speculative(self) -> tuple[str, ...]:
        return tuple(n.name for n in self.nodes if n.speculative)

    @property
    def uncertain(self) -> tuple[str, ...]:
        return tuple(k for k, d in zip(self.inputs, self.domains) if len(d) == 2)

    def environments(self):
        # Bit j of an environment index belongs to uncertain input j.
        q = len(self.uncertain)
        for i in range(1 << q):
            e = {k: d[0] for k, d in zip(self.inputs, self.domains)}
            e.update({k: (i >> j) & 1 for j, k in enumerate(self.uncertain)})
            yield e

    def to_dict(self) -> dict[str, Any]:
        return {'inputs': [{'id': k, 'domain': list(d), 'prediction': p}
                           for k, d, p in zip(self.inputs, self.domains, self.prediction)],
                'nodes': [{'id': n.name, 'op': n.op, 'args': list(n.args),
                           'speculative': n.speculative} for n in self.nodes],
                'observations': list(self.observations),
                'dependencies': [[a, n.name] for n in self.nodes for a in dict.fromkeys(n.args)]}


def load_graph(obj: dict[str, Any]) -> Graph:
    """Reject incomplete declared dependencies, malformed gates and effectful prefixes."""
    if not isinstance(obj, dict) or set(obj) != {'inputs', 'nodes', 'observations', 'dependencies'}:
        raise ValueError('graph requires inputs, nodes, observations, dependencies only')
    if not isinstance(obj['inputs'], list) or not isinstance(obj['nodes'], list):
        raise ValueError('inputs and nodes must be lists')
    if not 1 <= len(obj['inputs']) <= 24 or not 1 <= len(obj['nodes']) <= 10000:
        raise ValueError('structural input or node limit exceeded')
    names: set[str] = set()
    ins, doms, preds = [], [], []
    for entry in obj['inputs']:
        if not isinstance(entry, dict) or set(entry) != {'id', 'domain', 'prediction'}:
            raise ValueError('invalid input fields')
        k, d, p = entry['id'], entry['domain'], entry['prediction']
        if not isinstance(k, str) or not k or k in names:
            raise ValueError('duplicate or empty identifier')
        if (not isinstance(d, list) or d not in ([0], [1], [0, 1])
                or any(type(x) is not int for x in d)
                or type(p) is not int or p not in (0, 1)):
            raise ValueError('only canonical Boolean domains and Boolean predictions are valid')
        names.add(k); ins.append(k); doms.append(tuple(d)); preds.append(p)
    nodes = []
    edges = set()
    suffix = False
    for item in obj['nodes']:
        if not isinstance(item, dict) or set(item) != {'id', 'op', 'args', 'speculative'}:
            raise ValueError('invalid node fields')
        k, op, args, spec = item['id'], item['op'], item['args'], item['speculative']
        if not isinstance(k, str) or not k or k in names:
            raise ValueError('duplicate or empty identifier')
        if not isinstance(op, str) or op not in ARITY or not isinstance(args, list) or len(args) != ARITY[op]:
            raise ValueError('unsupported effect or wrong arity')
        if any(not isinstance(a, str) or a not in names for a in args):
            raise ValueError('unknown input, cycle, or non-topological order')
        if type(spec) is not bool or (suffix and spec):
            raise ValueError('speculative nodes must form a prefix')
        suffix = suffix or not spec
        edges.update((a, k) for a in args)
        names.add(k); nodes.append(Node(k, op, tuple(args), spec))
    given = obj['dependencies']
    if not isinstance(given, list) or any(not isinstance(x, list) or len(x) != 2
                                         or any(not isinstance(y, str) for y in x) for x in given):
        raise ValueError('malformed dependency list')
    gs = {tuple(x) for x in given}
    if len(gs) != len(given) or gs != edges:
        raise ValueError('declared dependencies must equal all syntactic operand edges')
    obs = obj['observations']
    if (not isinstance(obs, list) or not obs or any(not isinstance(x, str) for x in obs)
            or len(obs) != len(set(obs)) or any(x not in names for x in obs)):
        raise ValueError('invalid observation list')
    return Graph(tuple(ins), tuple(doms), tuple(preds), tuple(nodes), tuple(obs))


def operation(op: str, args: list[int], mask: int = 1) -> int:
    if op == 'zero': return 0
    if op == 'one': return mask
    if op == 'copy': return args[0]
    if op == 'not': return args[0] ^ mask
    if op == 'and': return args[0] & args[1]
    if op == 'or': return args[0] | args[1]
    if op == 'xor': return args[0] ^ args[1]
    raise ValueError('unrecognized operation')


def cache(graph: Graph) -> dict[str, int]:
    vals = dict(zip(graph.inputs, graph.prediction))
    out = {}
    for node in graph.nodes:
        if not node.speculative:
            break
        vals[node.name] = operation(node.op, [vals[a] for a in node.args])
        out[node.name] = vals[node.name]
    return out


def execute(graph: Graph, environment: dict[str, int], repair: set[str] | None = None):
    """repair=None means full reference; otherwise keep all unselected cached slots."""
    if set(environment) != set(graph.inputs):
        raise ValueError('environment has wrong inputs')
    if any(type(environment[k]) is not int or environment[k] not in d
           for k, d in zip(graph.inputs, graph.domains)):
        raise ValueError('environment is outside its declared domain')
    if repair is not None and not repair <= set(graph.speculative):
        raise ValueError('repair refers to a non-speculative node')
    old = cache(graph)
    vals = dict(environment)
    for node in graph.nodes:
        if node.speculative and repair is not None and node.name not in repair:
            vals[node.name] = old[node.name]
        else:
            vals[node.name] = operation(node.op, [vals[a] for a in node.args])
    return tuple(vals[o] for o in graph.observations)
