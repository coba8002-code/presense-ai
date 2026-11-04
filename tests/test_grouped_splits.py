import unittest
from training.data import split_records
from evaluation.duplicate_groups import review_groups
from training.autolearn import lineage, assert_disjoint


class GroupedSplitTests(unittest.TestCase):
    def test_external_benchmark_group_overlap_is_rejected(self):
        a=dict(animal_id='dog-a',recording_group='a',sha256='a'*64)
        b=dict(animal_id='dog-b',recording_group='b',sha256='b'*64)
        for key in ('household_id','source_id','duplicate_group'):
            with self.assertRaisesRegex(ValueError,'overlap'):
                assert_disjoint(lineage([{**a,key:'shared'}]),lineage([{**b,key:'shared'}]))
            with self.assertRaises(ValueError):
                assert_disjoint(lineage([a]),lineage([{**b,key:'shared'}]))

    def rows(self):
        return [dict(animal_id=f'dog-{i}',path=f'{i}-{label}',label=label) for i in range(9) for label in ['bark','background']]

    def test_transitive_household_source_duplicate_isolation(self):
        rows=self.rows()
        rows[0]['household_id']='home';rows[2]['household_id']='home'
        rows[3]['source_id']='source';rows[4]['source_id']='source'
        rows[5]['duplicate_group']='copy';rows[6]['duplicate_group']='copy'
        result=split_records(rows,42)
        owner={r['animal_id']:part for part,items in result.items() for r in items}
        self.assertEqual(len({owner[f'dog-{i}'] for i in range(4)}),1)
        self.assertEqual(result,split_records(rows[::-1],42))

    def test_insufficient_clusters_and_invalid_ids_fail(self):
        rows=self.rows()
        for row in rows:row['household_id']='same-home'
        with self.assertRaises(ValueError):split_records(rows,42)
        for value in ('unknown',None,'',False,' home '):
            rows=self.rows();rows[0]['duplicate_group']=value
            with self.assertRaises(ValueError):split_records(rows,42)

    def test_review_candidates_transitive_not_ground_truth(self):
        data={'files':[{'id':x,'raw_sha256':str(i)*64,'category':'dog','animal_id':None} for i,x in enumerate(['a','b','c','d'])],
              'raw_equal_pairs':[], 'canonical_equal_pairs':[],
              'similarity_candidates':[{'ids':['a','b']},{'ids':['b','c']}]}
        result=review_groups(data)
        self.assertEqual(len(result['groups']),1)
        self.assertEqual(result['groups'][0]['members'],['a','b','c'])
        self.assertEqual(result['unlinked_files'],['d'])
        self.assertFalse(result['training_approved'])
        data['similarity_candidates'].append({'ids':['a','missing']})
        with self.assertRaises(ValueError):review_groups(data)
