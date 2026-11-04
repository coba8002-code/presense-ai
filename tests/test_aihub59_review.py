import json
from pathlib import Path
import tempfile
import unittest
from scripts.aihub59_review import summarize

class AIHubReviewTests(unittest.TestCase):
    def test_species_scope_and_no_emotion_or_owner_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'dog.json').write_text(json.dumps({'species':'dog','seq':1,'action':'walk','owner':{'emotion':'private-claim'},'inspect':{'emotion':'expert-claim'},'annotations':[{'frame_number':1,'keypoints':{'1':{'x':4,'y':7}},'timestamp':99}]}))
            (root/'cat.json').write_text(json.dumps({'species':'cat'}))
            r=summarize(root);self.assertEqual(r['dog_labels'],1);self.assertEqual(r['cat_labels_excluded'],1)
            self.assertNotIn('private-claim',json.dumps(r));self.assertNotIn('expert-claim',json.dumps(r))
            row=r['review_queue'][0];self.assertIsNone(row['animal_id']);self.assertFalse(row['training_approved']);self.assertEqual(row['timestamp_unit'],'unverified')
    def test_unknown_schema_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'bad.json';path.write_text('{}')
            with self.assertRaises(ValueError):summarize(root)
            path.unlink();(root/'link.json').symlink_to('/etc/hosts')
            with self.assertRaises(ValueError):summarize(root)
