import copy
import unittest
from unittest.mock import patch
from speculation.validate import resource_guard
resource_guard()
from speculation.model import Graph,Node,load_graph
from speculation.builders import (gap_graph,full_observer,circuit_reduction,
                                  invalidation_gap_graph)
from speculation.bitcheck import analyze
from speculation.replay import run,certificate,verify,fullstate_costs
from speculation.baselines import descendant_invalidation,complete_state_mismatch
from speculation import validate

class SemanticsTests(unittest.TestCase):
    def test_roundtrip(self):
        g=gap_graph(3)
        self.assertEqual(load_graph(g.to_dict()),g)

    def test_gap_and_certificates(self):
        for p in (1,2,3):
            g=gap_graph(p);a=analyze(g)
            self.assertEqual((a.adaptive_min,a.uniform_min),(1,p))
            envs=list(g.environments())
            for mask in range(1<<a.p):
                repair={name for i,name in enumerate(g.speculative) if mask>>i&1}
                for row,e in enumerate(envs):
                    active={f's{i}' for i in range(p) if e[f'u{i}']==1}
                    expected=e['d']==0 or not active or bool(repair&active)
                    self.assertEqual(bool(a.good_environments(mask)>>row&1),expected)
                    self.assertEqual(run(g,e,repair)[0]==run(g,e,None)[0],expected)
            self.assertTrue(verify(g,certificate(g,1,'adaptive',a.pointwise_mask)))
            self.assertTrue(verify(g,certificate(g,p,'uniform',[a.uniform_mask])))

    def test_explicit_stack_deep_chain(self):
        nodes=tuple(Node(f'n{i}','copy',('d' if i==0 else f'n{i-1}',),True) for i in range(10000))
        g=load_graph(Graph(('d',),((0,1),),(0,),nodes,('n9999',)).to_dict())
        self.assertEqual(run(g,{'d':1},None)[0],[1])
        self.assertEqual(run(g,{'d':1},set(g.speculative))[0],[1])
        self.assertEqual(run(g,{'d':1},set(g.speculative)-{'n0'})[0],[0])

    def test_full_state_principal_family(self):
        g=full_observer(gap_graph(3));a=analyze(g)
        costs,masks,union=fullstate_costs(g)
        self.assertEqual(costs,a.pointwise_min)
        self.assertEqual(a.uniform_min,len(union))
        for mask in range(1<<a.p):
            R={n for j,n in enumerate(g.speculative) if mask>>j&1}
            for i,M in enumerate(masks):
                self.assertEqual(bool(a.good_environments(mask)>>i&1),M<=R)

    def test_no_speculative_gates(self):
        g=Graph(('d',),((0,1),),(0,),(Node('n','not',('d',),False),),('n',))
        a=analyze(load_graph(g.to_dict()))
        self.assertEqual((a.adaptive_min,a.uniform_min),(0,0))

    def test_fixed_actual_input_and_prediction(self):
        # A prediction outside a fixed actual domain is legal in this declared model.
        g=Graph(('d',),((1,),),(0,),(Node('n','copy',('d',),True),),('n',))
        a=analyze(load_graph(g.to_dict()))
        self.assertEqual((a.q,a.adaptive_min,a.uniform_min),(0,1,1))

    def test_duplicate_operand_is_one_edge(self):
        g=Graph(('d',),((0,1),),(0,),(Node('n','xor',('d','d'),True),),('n',))
        obj=g.to_dict()
        self.assertEqual(obj['dependencies'],[['d','n']])
        self.assertEqual(analyze(load_graph(obj)).uniform_min,0)

    def test_row_limit(self):
        with self.assertRaises(ValueError): analyze(gap_graph(3),max_rows=1)

    def test_certificate_rejects_noncanonical_values(self):
        g=gap_graph(1);a=analyze(g);doc=certificate(g,1,'uniform',[a.uniform_mask])
        doc['rows'][0]['environment']['d']=False
        with self.assertRaises(ValueError):verify(g,doc)

    def test_graph_rejects_every_unknown_edge(self):
        g=gap_graph(2)
        for i in range(len(g.to_dict()['dependencies'])):
            obj=g.to_dict();obj['dependencies'].pop(i)
            with self.assertRaises(ValueError):load_graph(obj)

    def test_descendant_invalidation_is_safe(self):
        g=gap_graph(4)
        for e in g.environments():
            repair=descendant_invalidation(g,e)
            self.assertEqual(run(g,e,repair)[0],run(g,e,None)[0])

    def test_invalidation_gap_is_tight(self):
        for p in range(1,9):
            g=invalidation_gap_graph(p)
            e={'d':1}
            self.assertEqual(len(descendant_invalidation(g,e)),p)
            self.assertEqual(complete_state_mismatch(g,e),{'s0'})
            self.assertEqual(analyze(g).pointwise_min[1],1)

    def test_observation_refinement_never_lowers_cost(self):
        weak=gap_graph(4);strong=full_observer(weak)
        a=analyze(weak);b=analyze(strong)
        self.assertTrue(all(y>=x for x,y in zip(a.pointwise_min,b.pointwise_min)))
        self.assertGreaterEqual(b.adaptive_min,a.adaptive_min)
        self.assertGreaterEqual(b.uniform_min,a.uniform_min)

    @staticmethod
    def wrong_zero_costs(graph):
        # Keep the success table intact; corrupt only an already-positive optimum.
        # Budget-threshold checks alone used to accept this incorrect report.
        result=analyze(graph)
        if result.adaptive_min == result.uniform_min == 1:
            result.pointwise_min=[0]*len(result.pointwise_min)
            result.uniform_min=0
        return result

    def test_relation_oracle_rejects_wrong_zero_costs(self):
        with patch('speculation.validate.analyze',side_effect=self.wrong_zero_costs):
            with self.assertRaises(AssertionError):validate.relations()

    def test_circuit_oracle_rejects_wrong_zero_costs(self):
        with patch('speculation.validate.analyze',side_effect=self.wrong_zero_costs):
            with self.assertRaises(AssertionError):validate.circuits()

if __name__=='__main__':unittest.main()
