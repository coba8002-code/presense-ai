import hashlib
import tempfile
from pathlib import Path
import subprocess
import unittest
import wave
import numpy as np
from evaluation.audio_duplicates import compare,decode

class ExpansionAuditTests(unittest.TestCase):
    def row(self,key,dataset,signal):
        digest=hashlib.sha256(key.encode()).hexdigest()
        return {'id':key,'dataset':dataset,'signal':signal,'raw_sha256':digest,'canonical_sha256':hashlib.sha256(signal.tobytes()).hexdigest()}
    def test_focus_scope_excludes_reference_pairs(self):
        x=np.random.default_rng(12).normal(0,.1,32000)
        rows=[self.row('new','extra',x),self.row('old1','esc10',x),self.row('old2','esc10',x)]
        r=compare(rows,focus_datasets=('extra',))
        self.assertEqual(r['compared_file_pairs'],2)
        self.assertNotIn(['old1','old2'],r['canonical_equal_pairs'])
        self.assertIn(['new','old1'],r['canonical_equal_pairs'])
    def test_skip_repeated_focus_internal_pairs(self):
        x=np.zeros(32000);rows=[self.row('a','extra',x),self.row('b','extra',x),self.row('old','esc10',x)]
        self.assertEqual(compare(rows,focus_datasets=('extra',),include_within_focus=False)['compared_file_pairs'],2)
    def test_mp3_decode_is_explicit_and_hash_bound(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);wav=root/'a.wav';mp3=root/'a.mp3'
            with wave.open(str(wav),'wb') as w:w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes((np.sin(np.arange(32000)/30)*12000).astype('<i2').tobytes())
            subprocess.run(['ffmpeg','-v','error','-i',str(wav),str(mp3)],check=True)
            digest=hashlib.sha256(mp3.read_bytes()).hexdigest()
            r=decode(mp3,digest,media_format='mp3');self.assertGreaterEqual(len(r['signal']),32000)
            with self.assertRaises(ValueError):decode(mp3,digest,media_format='http')
            with self.assertRaises(ValueError):decode(mp3,'0'*64,media_format='mp3')

class ExpansionQueueTests(unittest.TestCase):
    def test_prior_hash_bound_edges_extend_transitive_review_group(self):
        from evaluation.expansion_audio_audit import retain_prior,queue
        files=[{'id':key,'dataset':dataset,'raw_sha256':h*64,'canonical_sha256':h*64,'category':category} for key,dataset,h,category in [('a','zenodo-extra','a','growl'),('b','esc10','b','dog'),('c','barkmeow','c','dog')]]
        audit={'files':files,'raw_equal_pairs':[],'canonical_equal_pairs':[],'similarity_candidates':[{'ids':['a','b']}]}
        prior={'files':[{**files[1],'id':'old-b'},{**files[2],'id':'old-c'}],'raw_equal_pairs':[],'canonical_equal_pairs':[],'similarity_candidates':[{'ids':['old-b','old-c']}]}
        result=queue(retain_prior(audit,prior));entry=result['entries'][0]
        self.assertEqual(entry['linked_records'],['a','b','c']);self.assertIsNone(entry['animal_id']);self.assertIsNone(entry['reviewed_event_label']);self.assertFalse(entry['training_approved'])
        prior['files'][0]['raw_sha256']='d'*64
        with self.assertRaises(ValueError):retain_prior(audit,prior)
    def test_unknown_queue_edge_is_rejected(self):
        from evaluation.expansion_audio_audit import queue
        audit={'files':[{'id':'a','dataset':'red-library'}],'raw_equal_pairs':[['a','missing']],'canonical_equal_pairs':[],'similarity_candidates':[]}
        with self.assertRaises(ValueError):queue(audit)
