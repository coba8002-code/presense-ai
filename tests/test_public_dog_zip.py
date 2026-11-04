import io
import unittest
from scripts.public_dog_zip import RangeReader, dog_member

class PublicDogZipTests(unittest.TestCase):
    def test_only_explicit_dog_folders_and_safe_paths(self):
        self.assertEqual(dog_member('dataset/dog_growl_train/a.wav'),'growl')
        self.assertIsNone(dog_member('dataset/cat/a.wav'))
        self.assertIsNone(dog_member('dataset/merged_animal_datasets/dog.wav'))
        for p in ['dataset/dog_bark_train/../../a.wav','/dataset/dog_bark_train/a.wav','dataset/dog_bark_train/a\\b.wav']:
            with self.assertRaises(ValueError):dog_member(p)

    def test_range_requires_exact_206_and_truncation_rejected(self):
        class Response(io.BytesIO):
            status=200
            headers={}
        for status,header,data in [(200,None,b'1234'),(206,'bytes 0-3/4',b'123'),(206,'bytes 1-3/4',b'1234')]:
            def opener(req,timeout):
                r=Response(data);r.status=status;r.headers={'Content-Range':header};return r
            reader=RangeReader('https://example.invalid/file',4,opener=opener)
            with self.assertRaises(ValueError):reader.read(4)

    def test_seek_cache_and_bounds(self):
        calls=[]
        class Response(io.BytesIO):
            status=206
            headers={'Content-Range':'bytes 0-3/4'}
        def opener(req,timeout):calls.append(req);return Response(b'abcd')
        r=RangeReader('https://example.invalid/file',4,opener=opener)
        self.assertEqual(r.read(2),b'ab');r.seek(-1,2);self.assertEqual(r.read(4),b'd');self.assertEqual(len(calls),1)
        with self.assertRaises(ValueError):r.seek(-1)
