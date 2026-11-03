"""Unapproved image formats must never enter their Pillow decoder."""
import io
import unittest
from unittest.mock import patch
from training.small_vlm import image_from_bytes


class ImageDecoderBoundaryTests(unittest.TestCase):
    def test_rejects_gif_before_entering_decoder(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Optional Pillow environment required')
        Image.init()
        content=io.BytesIO();Image.new('RGB',(8,8)).save(content,format='GIF')
        _,accept=Image.OPEN['GIF']
        def forbidden(*args,**kwargs):raise AssertionError('Unapproved GIF decoder was entered')
        with patch.dict(Image.OPEN,{'GIF':(forbidden,accept)}):
            with self.assertRaises(ValueError):image_from_bytes(content.getvalue())

    def test_valid_png_and_jpeg_remain_supported(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Optional Pillow environment required')
        for fmt in ['PNG','JPEG']:
            content=io.BytesIO();Image.new('RGB',(8,8),(40,50,60)).save(content,format=fmt)
            image=image_from_bytes(content.getvalue())
            self.assertEqual(image.size,(8,8));self.assertEqual(image.mode,'RGB')
