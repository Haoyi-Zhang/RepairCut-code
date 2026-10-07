"""Finite portable checks of the current pure circuit validation functions.

The Linux campaign imports resource and enforces resource_guard. These tests do
not import that runner or replace its guards. Five current function definitions
are compiled unchanged from its AST, with a test-local first-loop bound of 16
instead of running its 128-case campaign. No result files or timings are written.
The regular CI still runs the entire guarded runner and discovers this file.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import random
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from speculation import builders, bitcheck, model, replay


def scalar_reference(graph, environment, repair):
    """Independent forward truth-table semantics; no production gate helpers."""
    tables = {"zero": (0,), "one": (1,), "copy": (0, 1), "not": (1, 0),
              "and": (0, 0, 0, 1), "or": (0, 1, 1, 1), "xor": (0, 1, 1, 0)}

    def gate(node, values):
        index = 0
        for name in node.args:
            index = 2 * index + values[name]
        return tables[node.op][index]

    predicted = dict(zip(graph.inputs, graph.prediction))
    for node in graph.nodes:
        predicted[node.name] = gate(node, predicted)
    values = dict(environment)
    for node in graph.nodes:
        values[node.name] = (predicted[node.name]
                            if repair is not None and node.speculative and node.name not in repair
                            else gate(node, values))
    return ([values[name] for name in graph.observations],
            {node.name: values[node.name] for node in graph.nodes},
            {node.name: predicted[node.name] for node in graph.nodes if node.speculative})


def pure_namespace(path=None):
    """Read actual current functions without editing them or running resource I/O."""
    path = Path(path) if path is not None else ROOT / "speculation/validate.py"
    names = {"require", "selected", "require_reduction_costs", "random_formula", "circuits"}
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in functions} != names or len(functions) != len(names):
        raise AssertionError("pure function inventory changed")
    namespace = dict(random=random, ARITY=model.ARITY, Node=model.Node, Graph=model.Graph,
                     load_graph=model.load_graph, relation_truth=builders.relation_truth,
                     circuit_reduction=builders.circuit_reduction, analyze=bitcheck.analyze,
                     run=replay.run)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace)
    first = True

    def finite_range(*args):
        nonlocal first
        if first:
            first = False
            if args != (128,):
                raise AssertionError("campaign loop changed; reconsider the finite bound")
            return range(16)
        return range(*args)

    namespace["range"] = finite_range
    return namespace


def capture(namespace, runner=replay.run):
    """All actual outputs/traces/cache checked; independent quantified minima."""
    digest = hashlib.sha256()
    reference_calls = 0
    formula_calls = 0
    mixed_calls = 0
    graphs, successes = {}, {}
    references_per_environment = {}

    def checked_run(graph, environment, repair):
        nonlocal reference_calls, formula_calls, mixed_calls
        if len(graph.speculative) > 7 or len(graph.inputs) > 3 or len(graph.nodes) > 128:
            raise AssertionError("finite fixture bound exceeded")
        actual = runner(graph, environment, repair)
        expected = scalar_reference(graph, environment, repair)
        if actual != expected:
            raise AssertionError("independent full replay disagreement")
        if not graph.speculative:
            formula_calls += 1
        else:
            key = json.dumps(graph.to_dict(), sort_keys=True)
            graphs.setdefault(key, graph)
            env = tuple(environment[name] for name in graph.inputs)
            if repair is None:
                reference_calls += 1
                count_key = (key, env)
                references_per_environment[count_key] = references_per_environment.get(count_key, 0) + 1
            else:
                mixed_calls += 1
                mask = sum(1 << j for j, name in enumerate(graph.speculative) if name in repair)
                good = actual[0] == scalar_reference(graph, environment, None)[0]
                rows = successes.setdefault(key, {})
                rows.setdefault(env, {})[mask] = good
                # The stream excludes redundant reference calls but retains mixed call order.
                digest.update(json.dumps([graph.to_dict(), environment, sorted(repair), actual],
                                         sort_keys=True, separators=(",", ":")).encode())
        return actual

    namespace["run"] = checked_run
    records, counters = namespace["circuits"]()
    if len(records) != len(graphs) or len(graphs) != 16:
        raise AssertionError("seeded prefix graph inventory changed")
    for record, (key, graph) in zip(records, graphs.items()):
        rows = successes[key]
        if len(rows) != len(list(graph.environments())) or any(
                set(row) != set(range(1 << len(graph.speculative))) for row in rows.values()):
            raise AssertionError("mask/environment coverage changed")
        pointwise = [min(mask.bit_count() for mask, good in rows[env].items() if good)
                     for env in rows]
        uniform = min(mask.bit_count() for mask in range(1 << len(graph.speculative))
                      if all(row[mask] for row in rows.values()))
        if record["adaptive"] != max(pointwise) or record["uniform"] != uniform:
            raise AssertionError("independent quantified minima disagreement")
    return dict(records=records, counters=counters, mixed_digest=digest.hexdigest(),
                reference_calls=reference_calls, formula_calls=formula_calls, mixed_calls=mixed_calls,
                references_per_environment=list(references_per_environment.values()), graphs=list(graphs.values()))


class CircuitReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.captured = capture(pure_namespace())

    def test_seeded_prefix_independent_minima_and_all_mask_order(self):
        result = self.captured
        self.assertEqual(result["counters"], dict(graph_instances=16, independent_replay_rows=5120, seed=1729))
        self.assertEqual([row["case"] for row in result["records"]], list(range(16)))
        self.assertEqual(result["mixed_calls"], 5120)
        self.assertEqual(result["formula_calls"], 128)
        self.assertEqual(result["reference_calls"], 96)
        self.assertEqual(result["references_per_environment"], [1] * 96)

    def test_all_primitives_prediction_domain_and_zero_prefix(self):
        for domain, prediction in (((0, 1), 0), ((1,), 0), ((0,), 1)):
            for speculative in (False, True):
                graph = model.Graph(("x",), (domain,), (prediction,), (
                    model.Node("z", "zero", (), speculative), model.Node("o", "one", (), speculative),
                    model.Node("c", "copy", ("x",), speculative), model.Node("n", "not", ("c",), speculative),
                    model.Node("a", "and", ("c", "c"), False), model.Node("r", "or", ("z", "n"), False),
                    model.Node("v", "xor", ("r", "o"), False)), ("a", "v"))
                graph = model.load_graph(graph.to_dict())
                saved = graph.to_dict()
                for env in graph.environments():
                    self.assertEqual(replay.run(graph, env, None), scalar_reference(graph, env, None))
                    for mask in range(1 << len(graph.speculative)):
                        repair = {name for j, name in enumerate(graph.speculative) if mask >> j & 1}
                        self.assertEqual(replay.run(graph, env, repair), scalar_reference(graph, env, repair))
                self.assertEqual(graph.to_dict(), saved)

    def test_exact_cost_negative_controls_remain(self):
        ns = pure_namespace()
        good = SimpleNamespace(pointwise_min=[0, 1, 0, 2], adaptive_min=2, uniform_min=2)
        oracle = dict(pointwise=[True, False], adaptive=False, uniform=False)
        ns["require_reduction_costs"](good, oracle, 1)
        for field, value, message in (("pointwise_min", [0, 0, 0, 2], "exact pointwise relation costs mismatch"),
                                      ("adaptive_min", 0, "exact adaptive relation cost mismatch"),
                                      ("uniform_min", 0, "exact uniform relation cost mismatch")):
            bad = copy.deepcopy(good)
            setattr(bad, field, value)
            with self.assertRaisesRegex(AssertionError, message):
                ns["require_reduction_costs"](bad, oracle, 1)

    def test_scalar_mixed_mismatch_is_not_hidden_by_hoisting(self):
        ns = pure_namespace()
        def corrupt(graph, env, repair):
            out, trace, old = replay.run(graph, env, repair)
            if repair is not None:
                out = [1 - scalar_reference(graph, env, None)[0][0]]
            return out, trace, old
        ns["run"] = corrupt
        with self.assertRaisesRegex(AssertionError, "circuit replay mismatch"):
            ns["circuits"]()

    def test_bit_evaluator_disagreement_remains_detected(self):
        ns = pure_namespace()
        def corrupt(graph):
            result = bitcheck.analyze(graph)
            class WrongSuccess:
                def __getattr__(self, name):
                    return getattr(result, name)
                def good_environments(self, mask):
                    return result.good_environments(mask) ^ 1
            return WrongSuccess()
        ns["analyze"] = corrupt
        with self.assertRaisesRegex(AssertionError, "circuit replay mismatch"):
            ns["circuits"]()

    def test_certificates_budget_trace_cache_and_typed_fields(self):
        for graph in self.captured["graphs"][:2]:
            environments = list(graph.environments())
            masks = []
            for env in environments:
                good = []
                for mask in range(1 << len(graph.speculative)):
                    repair = {name for j, name in enumerate(graph.speculative) if mask >> j & 1}
                    if scalar_reference(graph, env, repair)[0] == scalar_reference(graph, env, None)[0]:
                        good.append(mask)
                masks.append(min(good, key=lambda mask: (mask.bit_count(), mask)))
            budget = max(mask.bit_count() for mask in masks)
            document = replay.certificate(graph, budget, "adaptive", masks)
            self.assertTrue(replay.verify(graph, document))
            mutations = []
            bad = copy.deepcopy(document); bad["budget"] = True; mutations.append(bad)
            bad = copy.deepcopy(document); bad["rows"] = bad["rows"][:-1]; mutations.append(bad)
            bad = copy.deepcopy(document); bad["rows"][0]["selected"] = ["missing"]; mutations.append(bad)
            for field in ("environment", "cache", "trace"):
                bad = copy.deepcopy(document)
                key = next(iter(bad["rows"][0][field]))
                bad["rows"][0][field][key] = bool(bad["rows"][0][field][key])
                mutations.append(bad)
            bad = copy.deepcopy(document); bad["rows"][0]["output"][0] = True; mutations.append(bad)
            for bad in mutations:
                with self.assertRaises(ValueError):
                    replay.verify(graph, bad)


if __name__ == "__main__":
    unittest.main()
