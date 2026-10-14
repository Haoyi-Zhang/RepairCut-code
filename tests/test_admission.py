"""File-free admission checks; no large truth tables or measurement driver."""
import unittest
from unittest.mock import patch

from speculation import bitcheck
from speculation.model import Graph, Node, load_graph
from speculation.replay import run


def graph(prefix=1):
    nodes = tuple(Node(f's{i}', 'copy', ('d',), True) for i in range(prefix))
    return load_graph(Graph(('d',), ((0, 1),), (0,), nodes,
                            tuple(n.name for n in nodes)).to_dict())


class AdmissionTests(unittest.TestCase):
    def test_default_and_tighter_exact_limit_agree(self):
        small = graph()
        result = bitcheck.analyze(small, max_rows=4)
        self.assertEqual(result, bitcheck.analyze(small))
        self.assertEqual((result.rows, result.pointwise_min, result.uniform_min),
                         (4, [0, 1], 1))

    def test_tighter_limit_rejects_before_materialization(self):
        with patch.object(bitcheck, 'column', side_effect=AssertionError('allocated')):
            with self.assertRaisesRegex(ValueError, 'requires 4 rows'):
                bitcheck.analyze(graph(), max_rows=3)

    def test_caller_cannot_raise_hard_cap(self):
        with patch.object(bitcheck, 'column', side_effect=AssertionError('allocated')):
            for limit in (bitcheck.MAX_ROWS + 1, 2 * bitcheck.MAX_ROWS):
                with self.assertRaisesRegex(ValueError, 'hard cap cannot be raised'):
                    bitcheck.analyze(graph(), max_rows=limit)

    def test_invalid_limit_types_and_nonpositive_limits(self):
        for limit in (True, False, 1.0, 0, -1, None):
            with self.assertRaisesRegex(ValueError, 'max_rows must be an integer'):
                bitcheck.analyze(graph(), max_rows=limit)

    def test_valid_graph_above_cap_rejects_without_bit_vectors(self):
        # 25 cached copies + one uncertain input imply 2^26 rows. Only the
        # tiny graph is constructed; no truth vector is allocated.
        with patch.object(bitcheck, 'column', side_effect=AssertionError('allocated')):
            with self.assertRaisesRegex(ValueError, 'width 26 requires'):
                bitcheck.analyze(graph(prefix=25))

    def test_small_masks_still_match_scalar_replay(self):
        small = graph(prefix=2)
        result = bitcheck.analyze(small, max_rows=8)
        for mask in range(4):
            selected = {name for j, name in enumerate(small.speculative) if mask >> j & 1}
            for row, environment in enumerate(small.environments()):
                expected = run(small, environment, selected)[0] == run(small, environment, None)[0]
                self.assertEqual(bool(result.good_environments(mask) >> row & 1), expected)


if __name__ == '__main__':
    unittest.main()
