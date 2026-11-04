import unittest
from training.play_pant_research import partition_events,usable_events

class PlayPantTests(unittest.TestCase):
    def test_noise_overlap_short_and_other_labels_excluded(self):
        events=[{'tmin':'0','tmax':'1','tier':'calls','text':'Pant'}, {'tmin':'.5','tmax':'.8','tier':'noise','text':'Human'}, {'tmin':'2','tmax':'3','tier':'calls','text':'Growl'}, {'tmin':'4','tmax':'4.05','tier':'calls','text':'Grunt'}, {'tmin':'5','tmax':'6','tier':'calls','text':'Whine'}]
        result=usable_events(events,10)
        self.assertEqual([(r['label'],r['start']) for r in result],[('Growl',2.)])
    def test_complete_dog_separation_and_no_pcm_overlap(self):
        rows=[{'animal_id':f'play-pant:{i:02d}','source_id':f'session-{i}','path':f'{i}-{label}','label':label,'pcm_sha256':f'{i}-{label}'} for i in range(1,18) for label in ('Pant','Growl','Grunt')]
        parts=partition_events(rows)
        identities=[{r['animal_id'] for r in p} for p in parts.values()]
        self.assertFalse(identities[0]&identities[1]);self.assertFalse(identities[0]&identities[2]);self.assertFalse(identities[1]&identities[2])
        rows[-1]['pcm_sha256']=rows[0]['pcm_sha256']
        # Force a known cross-boundary PCM overlap using the actual split.
        keys=list(parts);a=parts[keys[0]][0];b=parts[keys[1]][0];b['pcm_sha256']=a['pcm_sha256']
        with self.assertRaises(ValueError):partition_events(rows)
    def test_invalid_annotation_clock_rejected(self):
        with self.assertRaises(ValueError):usable_events([{'tmin':'nan','tmax':'1','tier':'calls','text':'Pant'}],10)
    def test_test_features_cannot_change_fitted_weights(self):
        import numpy as np
        from training.play_pant_research import train
        rows=[{'animal_id':f'play-pant:{i:02d}','source_id':f'session-{i}','path':f'{i}-{label}','label':label,'pcm_sha256':f'{i}-{label}','feature_row':j*3+k} for j,i in enumerate(range(1,18)) for k,label in enumerate(('Growl','Grunt','Pant'))]
        x=np.random.default_rng(10).normal(size=(len(rows),4));_,a=train(rows,x)
        for r in partition_events(rows)['test']:x[r['feature_row']]+=1000
        _,b=train(rows,x);np.testing.assert_array_equal(a['weights'],b['weights']);np.testing.assert_array_equal(a['mean'],b['mean'])
    def test_old_or_conflicting_license_and_modified_source_rejected(self):
        import json,hashlib,tempfile
        from pathlib import Path
        from training.play_pant_research import validate_source,RECORD
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);files=[]
            for name in ['07 Readme.txt','05 Metadata.csv','04 Annotations.zip','03 Play session recordings.zip']:
                content=b'CC BY 4.0' if name.endswith('.txt') else b'fixture'
                (root/name).write_bytes(content);files.append({'key':name,'size':len(content),'checksum':'md5:'+hashlib.md5(content).hexdigest()})
            record={'id':RECORD,'metadata':{'license':{'id':'cc-by-4.0'}},'files':files};(root/'record.json').write_text(json.dumps(record));validate_source(root)
            (root/'05 Metadata.csv').write_bytes(b'changed')
            with self.assertRaises(ValueError):validate_source(root)
            # Matching checksums must not allow a contradictory NC README.
            (root/'05 Metadata.csv').write_bytes(b'fixture')
            content=b'CC BY 4.0 metadata, but Attribution NonCommercial 4.0 terms'
            (root/'07 Readme.txt').write_bytes(content);files[0].update(size=len(content),checksum='md5:'+hashlib.md5(content).hexdigest())
            (root/'record.json').write_text(json.dumps(record))
            with self.assertRaises(ValueError):validate_source(root)
            record['id']=18972388;(root/'record.json').write_text(json.dumps(record))
            with self.assertRaises(ValueError):validate_source(root)
