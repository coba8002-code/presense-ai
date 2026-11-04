import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from backend.vlm import observe, VisionInput
from backend.realtime import AudioEngine
from training.data import load_records
from training.video_review import proposals
from knowledge.pipeline import open_db, cycle, search
from knowledge.candidates import candidates
from knowledge.models import Analysis
from test_vlm import IMAGE, RESULT
from test_realtime import model, HEADERS, PCM
from test_foundation import request
from test_knowledge import config, FakeProviders, analysis


class DogScopeTests(unittest.TestCase):
    def test_cat_training_and_live_artifact_rejected(self):
        with self.assertRaises(ValueError):
            load_records('/missing','/missing','cat')
        with self.assertRaises(ValueError):
            AudioEngine(model(species='cat'))

    def test_cat_audio_request_rejected(self):
        with patch.dict(os.environ,{'PETSENSE_ENABLE_AUDIO':'true','PETSENSE_API_TOKEN':'test-token'}):
            response=asyncio.run(request('POST','/v1/audio/chunks',content=PCM,
                headers={**HEADERS,'X-Audio-Species':'cat'}))
            self.assertEqual(response.status_code,422)

    def test_cat_image_abstains_and_clears_behavior(self):
        async def scenario():
            data={**RESULT,'species':'cat','confidence':.99,'abstained':False,'hypotheses':['resting']}
            transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(data)}}]}))
            async with httpx.AsyncClient(transport=transport) as client:
                result=await observe(VisionInput(image_base64=IMAGE,consent=True),client,'test','test')
                self.assertTrue(result.abstained)
                self.assertEqual(result.posture,'unknown')
                self.assertEqual(result.hypotheses,['insufficient_context'])
        asyncio.run(scenario())

    def test_cat_video_is_not_indexed_or_synced_and_legacy_data_hidden(self):
        with tempfile.TemporaryDirectory() as folder:
            db=open_db(Path(folder)/'db');self.addCleanup(db.close)
            cfg=config().model_copy(update={'notebook':'projects/123/locations/global/notebooks/test'})
            provider=FakeProviders()
            provider.analyze=lambda _:Analysis.model_validate({**analysis(),'species':'cat'})
            cycle(db,cfg,provider,now=1000)
            self.assertEqual(provider.synced,0)
            self.assertEqual(search(db,cfg,'door',now=1001),[])
            # A pre-MVP stored cat analysis must also be excluded.
            db.execute('UPDATE videos SET analysis=?,analyzed=?,model=?',
                (json.dumps({**analysis(),'species':'cat'}),1000,cfg.gemini_model));db.commit()
            self.assertEqual(search(db,cfg,'door',now=1001),[])
            self.assertEqual(proposals(db,cfg,now=1001),[])
            self.assertEqual(candidates(db,cfg,now=1001)[0]['status'],'unsupported_species')

    def test_demo_has_no_cat_selection(self):
        response=asyncio.run(request('GET','/realtime'))
        self.assertNotIn('value="cat"',response.text)
