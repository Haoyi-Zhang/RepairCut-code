"""Exact bit-parallel enumeration, intentionally exponential in the declared width."""
from __future__ import annotations
from dataclasses import dataclass
from .model import Graph, operation, cache

MAX_ROWS = 1 << 25

def column(bit: int, nbits: int) -> int:
    rows = 1 << nbits
    if nbits < 3:
        return sum(((i >> bit) & 1) << i for i in range(rows))
    nbytes = rows >> 3
    if bit < 3:
        return int.from_bytes(bytes((0xAA, 0xCC, 0xF0)[bit:bit+1]) * nbytes, 'little')
    half = 1 << (bit-3)
    pattern = bytes(half) + bytes([255])*half
    return int.from_bytes(pattern * (nbytes // len(pattern)), 'little')

@dataclass
class Result:
    q: int
    p: int
    rows: int
    good_bytes: bytes
    pointwise_min: list[int]
    pointwise_mask: list[int]
    uniform_min: int
    uniform_mask: int

    @property
    def adaptive_min(self):
        return max(self.pointwise_min)

    def good_environments(self, repair_mask: int) -> int:
        if not 0 <= repair_mask < (1 << self.p):
            raise ValueError('repair mask outside width')
        e = 1 << self.q
        if e < 8:
            pos = repair_mask*e
            return (self.good_bytes[pos//8] >> (pos % 8)) & ((1 << e)-1)
        stride = e//8
        start = repair_mask*stride
        return int.from_bytes(self.good_bytes[start:start+stride], 'little')


def analyze(graph: Graph, max_rows: int = MAX_ROWS) -> Result:
    q, p = len(graph.uncertain), len(graph.speculative)
    total_bits = q+p
    rows = 1 << total_bits
    if rows > max_rows:
        raise ValueError(f'width {total_bits} requires {rows} rows; limit is {max_rows}')
    # A conservative bit-vector payload admission rule, independent of available RSS.
    if rows * (2*len(graph.nodes)+p+q+8) // 8 > 2_000_000_000:
        raise ValueError('estimated Boolean payload exceeds 2 GB admission limit')
    allbits = (1 << rows)-1
    unknown = {x: j for j, x in enumerate(graph.uncertain)}
    vals, ref = {}, {}
    for k, d in zip(graph.inputs, graph.domains):
        v = column(unknown[k], total_bits) if k in unknown else (allbits if d[0] else 0)
        vals[k] = ref[k] = v
    old = cache(graph)
    j = 0
    for n in graph.nodes:
        fresh = operation(n.op, [vals[a] for a in n.args], allbits)
        if n.speculative:
            selector = column(q+j, total_bits)
            vals[n.name] = (fresh & selector) | ((allbits ^ selector) if old[n.name] else 0)
            j += 1
        else:
            vals[n.name] = fresh
        ref[n.name] = operation(n.op, [ref[a] for a in n.args], allbits)
    good = allbits
    for o in graph.observations:
        good &= allbits ^ (vals[o] ^ ref[o])
    gb = good.to_bytes((rows+7)//8, 'little')
    del vals, ref, good, allbits
    envs = 1 << q
    res = Result(q, p, rows, gb, [p+1]*envs, [-1]*envs, p+1, -1)
    full = (1 << envs)-1
    for mask in range(1 << p):
        truth = res.good_environments(mask)
        if not truth:
            continue
        cost = mask.bit_count()
        if truth == full and cost < res.uniform_min:
            res.uniform_min, res.uniform_mask = cost, mask
        todo = truth
        while todo:
            lsb = todo & -todo
            u = lsb.bit_length()-1
            if cost < res.pointwise_min[u]:
                res.pointwise_min[u], res.pointwise_mask[u] = cost, mask
            todo ^= lsb
    # Full replay is a semantic invariant, not a fallback answer.
    if any(x > p for x in res.pointwise_min) or res.uniform_min > p:
        raise AssertionError('full replay did not agree with the reference')
    return res
