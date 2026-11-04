import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.acquire_play_pant import fetch_file,RECORD

class PlayPantAcquisitionTests(unittest.TestCase):
    def test_complete_small_source_requires_publisher_checksum(self):
        data=b'CC BY 4.0';entry={'size':len(data),'checksum':'md5:'+hashlib.md5(data).hexdigest(),'links':{'self':f'https://zenodo.org/api/records/{RECORD}/files/readme/content'}}
        with tempfile.TemporaryDirectory() as d,patch('urllib.request.urlopen',side_effect=lambda *a,**k:io.BytesIO(data)):
            path=Path(d)/'README';r=fetch_file(entry,path);self.assertEqual(path.read_bytes(),data);self.assertEqual(r['sha256'],hashlib.sha256(data).hexdigest())
            entry['checksum']='md5:'+'0'*32
            with self.assertRaises(ValueError):fetch_file(entry,Path(d)/'bad')
            self.assertFalse((Path(d)/'bad').exists())
    def test_large_source_does_not_accept_full_200_response(self):
        class Response(io.BytesIO):
            status=200
            headers={}
        entry={'size':1000001,'checksum':'md5:'+'0'*32,'links':{'self':f'https://zenodo.org/api/records/{RECORD}/files/audio/content'}}
        with tempfile.TemporaryDirectory() as d,patch('urllib.request.urlopen',side_effect=lambda *a,**k:Response(b'')):
            with self.assertRaises(ValueError):fetch_file(entry,Path(d)/'archive')
            self.assertFalse((Path(d)/'archive').exists())
