import asyncio
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave
import numpy as np
from test_foundation import request
from backend.app import app
from backend.realtime import AudioEngine, Admission, analyze_pcm
from training.audio import features, pcm_features

PCM = (np.sin(np.arange(16000) * 2 * np.pi * 500 / 16000) * 10000).astype('<i2').tobytes()
HEADERS = {'Authorization': 'Bearer test-token', 'Content-Type': 'application/octet-stream',
           'X-Audio-Consent': 'true', 'X-Audio-Species': 'dog', 'X-Audio-Sequence': '7'}


def model(**changes):
    from training.audio import FEATURE_VERSION
    value = dict(format_version=1, feature_version=FEATURE_VERSION, species='dog',
                 labels=['bark', 'other'], mean=[0.] * 34, scale=[1.] * 34,
                 weights=[[0., 0.]] * 35, threshold=.7, synthetic=False)
    return {**value, **changes}


class RealtimeTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'PETSENSE_ENABLE_AUDIO': 'true',
                             'PETSENSE_API_TOKEN': 'test-token', 'PETSENSE_AUDIO_MODEL': '',
                             'PETSENSE_AUDIO_MODEL_APPROVED': 'false'})
        self.env.start()
        self.addCleanup(self.env.stop)
        app.state.audio_admission = Admission()

    def post(self, body=PCM, headers=None):
        return asyncio.run(request('POST', '/v1/audio/chunks', content=body,
                                   headers=HEADERS if headers is None else headers))

    def test_sound_activity_without_model_abstains(self):
        result = self.post()
        self.assertEqual(result.status_code, 200)
        body = result.json()
        self.assertEqual(body['sequence'], 7)
        self.assertTrue(body['sound_activity'])
        self.assertEqual(body['status'], 'model_unavailable')
        self.assertTrue(body['abstained'])
        self.assertIsNone(body['prediction'])
        self.assertEqual(body['audio_ms'], 1000)

    def test_silence_is_not_an_animal_prediction(self):
        response = self.post(b'\x00' * 32000).json()
        self.assertEqual(response['status'], 'quiet')
        self.assertFalse(response['sound_activity'])
        self.assertIsNone(response['prediction'])

    def test_auth_consent_and_feature_flag(self):
        self.assertEqual(self.post(headers={**HEADERS, 'Authorization': 'Bearer wrong'}).status_code, 401)
        self.assertEqual(self.post(headers={**HEADERS, 'X-Audio-Consent': 'false'}).status_code, 403)
        with patch.dict(os.environ, {'PETSENSE_ENABLE_AUDIO': 'false'}):
            self.assertEqual(self.post().status_code, 503)

    def test_bad_audio_and_metadata(self):
        for body in (b'', b'\x00' * 3199, b'\x00' * 32001):
            app.state.audio_admission = Admission()
            self.assertIn(self.post(body).status_code, (413, 422))
        for key, value in [('X-Audio-Species', 'human'), ('X-Audio-Sequence', '-1'),
                           ('Content-Type', 'audio/wav')]:
            app.state.audio_admission = Admission()
            self.assertIn(self.post(headers={**HEADERS, key: value}).status_code, (415, 422))

    def test_request_limit_is_bounded(self):
        admission = Admission(clock=lambda: 10.)
        for _ in range(5):
            admission.enter()
            admission.leave()
        with self.assertRaises(ValueError):
            admission.enter()
        self.assertEqual(admission.active, 0)
        self.assertEqual(len(admission.arrivals), 5)

    def test_parallel_limit_released(self):
        admission = Admission(clock=lambda: 10.)
        admission.enter()
        admission.enter()
        with self.assertRaises(ValueError):
            admission.enter()
        admission.leave()
        admission.enter()
        self.assertEqual(admission.active, 2)

    def test_pcm_features_match_training_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'audio.wav'
            with wave.open(str(path), 'wb') as wav:
                wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                wav.writeframes(PCM)
            np.testing.assert_array_equal(features(path), pcm_features(PCM))

    def test_model_threshold_and_species_mismatch(self):
        engine = AudioEngine(model())
        result = analyze_pcm(PCM, 'dog', 0, engine)
        self.assertTrue(result['abstained'])
        self.assertEqual(result['status'], 'low_confidence')
        self.assertIsNone(result['prediction'])
        self.assertEqual(analyze_pcm(PCM, 'cat', 0, engine)['status'], 'species_mismatch')
        weights = [[0., 0.]] * 34 + [[5., 0.]]
        result = analyze_pcm(PCM, 'dog', 0, AudioEngine(model(weights=weights)))
        self.assertEqual(result['prediction'], 'bark')
        self.assertFalse(result['abstained'])
        self.assertEqual(result['confidence_kind'], 'uncalibrated')

    def test_rejects_synthetic_invalid_and_nonfinite_models(self):
        for value in [model(synthetic=True), model(threshold=float('nan')),
                      model(scale=[0.] * 34), model(labels=['same', 'same']),
                      model(format_version=2), model(species='human')]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                AudioEngine(value)

    def test_static_demo_has_no_external_dependencies(self):
        response = asyncio.run(request('GET', '/realtime'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('마이크', response.text)
        self.assertIn('no-store', response.headers['cache-control'])

    def test_unapproved_model_path_is_never_opened(self):
        with patch.dict(os.environ, {'PETSENSE_AUDIO_MODEL': '/not-a-real-model.json'}), \
             patch('backend.realtime.load_engine', side_effect=AssertionError('read unapproved model')):
            self.assertEqual(self.post().json()['status'], 'model_unavailable')

    def test_invalid_approved_model_is_generic_and_releases_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.json'
            path.write_text(json.dumps(model(synthetic=True)))
            with patch.dict(os.environ, {'PETSENSE_AUDIO_MODEL': str(path), 'PETSENSE_AUDIO_MODEL_APPROVED': 'true'}):
                response = self.post()
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(directory, response.text)
                self.assertEqual(app.state.audio_admission.active, 0)

    def test_rate_limited_route_and_recovery(self):
        now = [10.]
        app.state.audio_admission = Admission(clock=lambda: now[0])
        for _ in range(5):
            self.assertEqual(self.post().status_code, 200)
        response = self.post()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '1')
        now[0] = 11.1
        self.assertEqual(self.post().status_code, 200)

    def test_static_asset_allowlist(self):
        for name in ('client.js', 'capture.js'):
            response = asyncio.run(request('GET', f'/realtime/{name}'))
            self.assertEqual(response.status_code, 200)
            self.assertIn('javascript', response.headers['content-type'])
        self.assertEqual(asyncio.run(request('GET', '/realtime/secret')).status_code, 404)
