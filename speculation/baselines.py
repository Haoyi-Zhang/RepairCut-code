"""Transparent conservative repair policies for dependency-complete Boolean DAGs."""
from __future__ import annotations

from .model import Graph


def changed_inputs(graph: Graph, environment: dict[str, int]) -> set[str]:
    """Inputs whose revealed value differs from the declared prediction."""
    if set(environment) != set(graph.inputs):
        raise ValueError('environment keys do not match')
    changed: set[str] = set()
    for name, domain, prediction in zip(graph.inputs, graph.domains, graph.prediction):
        value = environment[name]
        if type(value) is not int or value not in domain:
            raise ValueError('environment is not admissible')
        if value != prediction:
            changed.add(name)
    return changed


def descendant_invalidation(graph: Graph, environment: dict[str, int]) -> set[str]:
    """Repair every cached prefix node reachable from a changed input.

    Reachability is computed from the exact operand edges already validated by
    ``load_graph``.  Because speculative nodes form a topological prefix, a
    single forward pass suffices.  This is a conservative policy: it is not an
    optimality oracle and deliberately ignores semantic cancellation.
    """
    dirty: set[str] = changed_inputs(graph, environment)
    repair: set[str] = set()
    for node in graph.nodes:
        if not node.speculative:
            break
        if any(arg in dirty for arg in node.args):
            dirty.add(node.name)
            repair.add(node.name)
    return repair


def complete_state_mismatch(graph: Graph, environment: dict[str, int]) -> set[str]:
    """Unique least repair for a complete-state observer.

    Imported lazily to keep this policy implementation independent of the exact
    bit-parallel analyzer.  The replay semantics, rather than ``bitcheck``,
    computes both the cache and fresh reference.
    """
    from .replay import run

    _, reference, old = run(graph, environment, None)
    return {name for name in graph.speculative if reference[name] != old[name]}
