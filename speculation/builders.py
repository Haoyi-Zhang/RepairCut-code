"""Transparent scientific input constructors; no downloaded program execution."""
from __future__ import annotations
from .model import Graph, Node, load_graph

class Builder:
    def __init__(self, q: int, uncertain_d: bool = True):
        if not 0 <= q <= 12:
            raise ValueError('q outside supported constructor range')
        self.q = q
        self.uncertain_d = uncertain_d
        self.nodes: list[Node] = []
        self.counter = 0

    def node(self, op, *args, name=None, spec=False):
        if name is None:
            name = f'g{self.counter}'
            self.counter += 1
        self.nodes.append(Node(name, op, tuple(args), spec))
        return name

    def combine(self, op, args, spec=False):
        args = list(args)
        if not args:
            return self.node('one' if op == 'and' else 'zero', spec=spec)
        out = args[0]
        for x in args[1:]:
            out = self.node(op, out, x, spec=spec)
        return out

    def finish(self, observations):
        ins = ('d',) + tuple(f'u{i}' for i in range(self.q))
        g = Graph(ins, (((0, 1),) if self.uncertain_d else ((1,),)) + ((0, 1),)*self.q, (0,)*len(ins),
                  tuple(self.nodes), tuple(observations))
        return load_graph(g.to_dict())


def reduction(q: int, m: int, truth_table: int | None = None,
              clauses: list[list[tuple[int, bool]]] | None = None,
              escape_length: int | None = None, uncertain_d: bool = True) -> Graph:
    """Build the selection/escape reduction. F variables: u first, then t.

    For tables, bit index = sum(u[j]*2**j) + sum(t[j]*2**(q+j)).
    clauses are CNF over variable indices; True denotes a positive literal.
    escape_length exists ONLY for a documented negative-control mutation.
    """
    if not 1 <= m <= 12 or (truth_table is None) == (clauses is None):
        raise ValueError('supply one formula representation and 1 <= m <= 12')
    b = Builder(q, uncertain_d)
    ts, fs = [], []
    for i in range(m):
        ts.append(b.node('copy', 'd', name=f't{i}', spec=True))
        fs.append(b.node('copy', 'd', name=f'f{i}', spec=True))
    e = 'd'
    length = m + 1 if escape_length is None else escape_length
    if length < 1:
        raise ValueError('escape chain must be nonempty')
    for j in range(length):
        e = b.node('copy', e, name=f'e{j}', spec=True)
    xs = [f'u{i}' for i in range(q)] + ts
    neg = [b.node('not', x) for x in xs]
    if truth_table is not None:
        if not 0 <= truth_table < (1 << (1 << (q+m))):
            raise ValueError('truth table is outside its Boolean width')
        terms = []
        for word in range(1 << (q+m)):
            if (truth_table >> word) & 1:
                terms.append(b.combine('and', [x if (word >> j) & 1 else neg[j]
                                               for j, x in enumerate(xs)]))
        formula = b.combine('or', terms)
    else:
        cvars = []
        for clause in clauses:
            if any(not 0 <= j < len(xs) for j, sign in clause):
                raise ValueError('CNF variable index out of range')
            cvars.append(b.combine('or', [xs[j] if sign else neg[j] for j, sign in clause]))
        formula = b.combine('and', cvars)
    onehot = b.combine('and', [b.node('xor', t, f) for t, f in zip(ts, fs)])
    result = b.node('or', e, b.node('and', onehot, formula))
    return b.finish([result])


def relation_truth(table: int, q: int, m: int):
    """Independent direct quantified relation, before any graph construction."""
    rows = [[(table >> (u | (x << q))) & 1 for x in range(1 << m)]
            for u in range(1 << q)]
    return {
        'adaptive': all(any(row) for row in rows),
        'uniform': any(all(rows[u][x] for u in range(1 << q)) for x in range(1 << m)),
        'pointwise': [any(row) for row in rows]
    }


def gap_graph(m: int) -> Graph:
    """A=1, U=m: one selectable cached bit per possible active input."""
    if not 1 <= m <= 12:
        raise ValueError('gap dimension must be 1..12')
    b = Builder(m)
    ss = [b.node('copy', 'd', spec=True, name=f's{i}') for i in range(m)]
    terms = [b.node('and', f'u{i}', s) for i, s in enumerate(ss)]
    return b.finish([b.combine('or', terms)])


def invalidation_gap_graph(p: int) -> Graph:
    """Complete-state family where reachability invalidates p slots but one differs.

    With prediction d=0 and revealed d=1, s0=COPY(d) changes while every
    sj=XOR(d,d), j>0, remains zero.  All p nodes are nevertheless syntactic
    descendants of the changed input.
    """
    if not 1 <= p <= 12:
        raise ValueError('prefix width must be 1..12')
    b = Builder(0)
    b.node('copy', 'd', spec=True, name='s0')
    for i in range(1, p):
        b.node('xor', 'd', 'd', spec=True, name=f's{i}')
    return b.finish([n.name for n in b.nodes])


def full_observer(graph: Graph) -> Graph:
    """Observe all prefix slots, retaining any original observations."""
    obj = graph.to_dict()
    obj['observations'] = list(dict.fromkeys(graph.speculative + graph.observations))
    return load_graph(obj)


def fullstate_cnf(q: int, clauses: list[list[tuple[int, bool]]], mode: str):
    """Polynomial coNP-hardness padding constructions. All gates are speculative.

    mode 'adaptive' duplicates each masked clause; mode 'uniform' duplicates
    the masked formula. Returns graph, threshold, metadata. No SAT solver used.
    """
    if mode not in ('adaptive', 'uniform') or not clauses:
        raise ValueError('nonempty clauses and a valid mode are required')
    b = Builder(q)
    xs = [f'u{i}' for i in range(q)]
    neg = [b.node('not', x, spec=True) for x in xs]
    terms = []
    for clause in clauses:
        if any(not 0 <= j < q for j, _ in clause):
            raise ValueError('literal index is out of range')
        terms.append(b.combine('or', [xs[j] if sign else neg[j] for j, sign in clause], spec=True))
    if mode == 'uniform':
        terms = [b.combine('and', terms, spec=True)]
    zs = [b.node('and', 'd', c, spec=True) for c in terms]
    nbase = len(b.nodes)
    copies = nbase + 1
    for z in zs:
        for _ in range(copies):
            b.node('copy', z, spec=True)
    k = nbase if mode == 'uniform' else copies*len(clauses)-1
    graph = b.finish([n.name for n in b.nodes])
    return graph, k, {'base': nbase, 'copies_per_group': copies, 'groups': len(zs)}


def correlated_components() -> Graph:
    b = Builder(1)
    a = b.node('copy', 'd', spec=True)
    c = b.node('copy', 'd', spec=True)
    out1 = b.node('and', 'u0', a)
    out2 = b.node('and', b.node('not', 'u0'), c)
    return b.finish([out1, out2])


def monotone_reduction(q: int, m: int, truth_table: int, escape_length=None):
    """Table-specialized monotone-in-prefix form of the general dual-rail reduction.

    Negative existential literals use the f rail, never NOT(t). Universal
    input negations are fresh. In the theorem an arbitrary circuit is translated
    by keeping its positive and negative rails, with linear-size overhead.
    """
    if not 1 <= m <= 12 or not 0 <= truth_table < (1 << (1 << (q+m))):
        raise ValueError('invalid dimensions or table')
    b = Builder(q)
    ts, fs = [], []
    for i in range(m):
        ts.append(b.node('copy', 'd', name=f't{i}', spec=True))
        fs.append(b.node('copy', 'd', name=f'f{i}', spec=True))
    e = 'd'
    length = m+1 if escape_length is None else escape_length
    if type(length) is not int or length < 1:
        raise ValueError('escape chain must be nonempty')
    for i in range(length):
        e = b.node('copy', e, name=f'e{i}', spec=True)
    us = [f'u{i}' for i in range(q)]
    ns = [b.node('not', u) for u in us]
    terms = []
    for assignment in range(1 << (q+m)):
        if (truth_table >> assignment) & 1:
            literals = [(us[i] if assignment >> i & 1 else ns[i]) for i in range(q)]
            literals += [(ts[i] if assignment >> (q+i) & 1 else fs[i]) for i in range(m)]
            terms.append(b.combine('and', literals))
    formula = b.combine('or', terms)
    cover = b.combine('and', [b.node('or', t, f) for t, f in zip(ts, fs)])
    return b.finish([b.node('or', e, b.node('and', cover, formula))])


def circuit_reduction(formula: Graph, q: int, m: int) -> Graph:
    """Linear-size dual-rail translation of an arbitrary validated Boolean circuit.

    The first q formula inputs are universal and the next m existential.
    Formula gates must all be fresh; exactly one output is required.
    """
    formula = load_graph(formula.to_dict())
    if (not 0 <= q <= 12 or not 1 <= m <= 12
            or len(formula.inputs) != q+m or len(formula.observations) != 1
            or formula.speculative or any(d != (0, 1) for d in formula.domains)):
        raise ValueError('formula dimensions, domain, or prefix are invalid')
    b = Builder(q)
    ts, fs = [], []
    for i in range(m):
        ts.append(b.node('copy', 'd', name=f't{i}', spec=True))
        fs.append(b.node('copy', 'd', name=f'f{i}', spec=True))
    escape = 'd'
    for j in range(m+1):
        escape = b.node('copy', escape, name=f'e{j}', spec=True)
    rails = {}
    for i, name in enumerate(formula.inputs):
        if i < q:
            u = f'u{i}'
            rails[name] = (u, b.node('not', u))
        else:
            rails[name] = (ts[i-q], fs[i-q])
    for n in formula.nodes:
        a = [rails[x] for x in n.args]
        if n.op in ('zero', 'one'):
            rails[n.name] = (b.node(n.op), b.node('one' if n.op == 'zero' else 'zero'))
        elif n.op == 'copy':
            rails[n.name] = a[0]
        elif n.op == 'not':
            rails[n.name] = (a[0][1], a[0][0])
        elif n.op in ('and', 'or'):
            other = 'or' if n.op == 'and' else 'and'
            rails[n.name] = (b.node(n.op, a[0][0], a[1][0]),
                            b.node(other, a[0][1], a[1][1]))
        elif n.op == 'xor':
            rails[n.name] = (
                b.node('or', b.node('and', a[0][0], a[1][1]),
                       b.node('and', a[0][1], a[1][0])),
                b.node('or', b.node('and', a[0][0], a[1][0]),
                       b.node('and', a[0][1], a[1][1])))
        else:
            raise ValueError('unsupported formula primitive')
    positive = rails[formula.observations[0]][0]
    cover = b.combine('and', [b.node('or', t, f) for t, f in zip(ts, fs)])
    return b.finish([b.node('or', escape, b.node('and', cover, positive))])
