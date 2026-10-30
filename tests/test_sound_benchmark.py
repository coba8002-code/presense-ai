import unittest
from evaluation.sound_benchmark import ranking_metrics

class RankingMetricsTests(unittest.TestCase):
    def test_perfect_and_reverse(self):
        self.assertEqual(ranking_metrics([1,0],[.9,.1])['auroc'],1)
        self.assertEqual(ranking_metrics([1,0],[.1,.9])['auroc'],0)
    def test_ties_and_precision(self):
        r=ranking_metrics([1,0,1,0],[.5,.5,.5,.5])
        self.assertEqual(r['auroc'],.5);self.assertEqual(r['average_precision'],.5)
        self.assertAlmostEqual(ranking_metrics([1,0,1],[.9,.8,.7])['average_precision'],(1+2/3)/2)
    def test_permutation_of_tied_items_does_not_change_result(self):
        self.assertEqual(ranking_metrics([1,0,0],[.5,.5,.1]),ranking_metrics([0,1,0],[.5,.5,.1]))
    def test_reject_invalid_or_degenerate(self):
        for labels,scores in [([],[]),([1],[.5]),([1,0],[float('nan'),.2]),([1,0],[2,0]),([1,0],[.5]),([2,0],[.2,.3])]:
            with self.subTest(labels=labels),self.assertRaises(ValueError):ranking_metrics(labels,scores)
