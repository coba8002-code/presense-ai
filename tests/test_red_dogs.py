import unittest
from scripts.acquire_red_dogs import entries,ITEM

class RedDogsTests(unittest.TestCase):
    def data(self):return {'metadata':{'identifier':ITEM,'licenseurl':'https://creativecommons.org/publicdomain/zero/1.0/'},'files':[{'name':'R01-dog.mp3','size':'100','md5':'a'*32}]}
    def test_bound_source_and_license(self):
        d=self.data();self.assertEqual(len(entries(d)),1);d['metadata']['licenseurl']='unknown'
        with self.assertRaises(ValueError):entries(d)
    def test_paths_duplicates_and_size_are_rejected(self):
        for name,size in [('../R01.mp3',1),('R01\\dog.mp3',1),('R01.mp3',10000001)]:
            d=self.data();d['files'][0].update(name=name,size=size)
            with self.assertRaises(ValueError):entries(d)
        d=self.data();d['files']*=2
        with self.assertRaises(ValueError):entries(d)
