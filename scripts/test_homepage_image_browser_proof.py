"""Pixel and identity adversaries, run by the normal protected unit entrypoint."""
import copy
import os
from pathlib import Path
import subprocess
import sys
import unittest
from PIL import Image
import homepage_image_browser_proof as proof


class HomepageImageBrowserProofTests(unittest.TestCase):
    def test_protected_unit_import_does_not_require_playwright(self):
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent))
        subprocess.run([sys.executable, '-c', "import sys;sys.modules['playwright']=None;import homepage_image_browser_proof;import test_homepage_image_browser"], env=env, check=True)

    def setUp(self):
        self.image = Image.new('RGBA', (30, 20), (100, 100, 100, 255))
        selected = {identity: {'rect': [x, 50, 8, 8], 'grid': [0, 50, 30, 20]}
                    for identity, x in zip(proof.ENCODED, (1, 11, 21))}
        state = {'dpr': 1, 'viewport': [30, 80], 'overflow': 0, 'section': [0, 50, 30, 20],
                 'header': [0, 0, 30, 20], 'selected': selected, 'target_unobscured': True,
                 'saudi_unobscured': True, 'scroll': [0, 1000], 'filter': 'none'}
        self.record = {'encoded_sha256': dict(proof.ENCODED),
                       'native_rgba': {identity: {'width': 1280, 'height': 720, 'rgba_sha256': '1'*64} for identity in proof.ENCODED},
                       'dom_sha256': '2'*64, 'target': proof.SAUDI,
                       'clip': {'x': 0, 'y': 50, 'width': 30, 'height': 20}, 'state': state, 'after_state': copy.deepcopy(state)}

    def compare(self, image=None, record=None):
        return proof.compare(self.image, image or self.image, self.record, record or self.record)

    def test_exact_and_bounded_saudi_residual_are_reported(self):
        self.assertTrue(self.compare()['exact_pixels'])
        image = self.image.copy(); image.putpixel((2, 2), (103, 98, 101, 255))
        result = self.compare(image)
        self.assertTrue(result['passed']); self.assertFalse(result['exact_pixels'])
        self.assertEqual(result['mismatch_pixels'], 1)
        self.assertEqual(result['maximum_rgb_delta'], 3)
        self.assertEqual(result['outside_saudi_pixels'], 0)
        self.assertEqual(result['histogram'], {'0': 599, '3': 1})

    def test_four_level_or_alpha_change_in_saudi_rejects(self):
        for color in ((104,100,100,255), (100,100,100,254)):
            with self.subTest(color=color):
                image = self.image.copy(); image.putpixel((2, 2), color)
                self.assertFalse(self.compare(image)['passed'])

    def test_every_outside_gulf_adonis_and_border_change_rejects(self):
        for point in ((0,0), (9,2), (12,2), (22,2), (2,8), (29,19)):
            with self.subTest(point=point):
                image = self.image.copy(); image.putpixel(point, (101,100,100,255))
                result = self.compare(image)
                self.assertFalse(result['passed']); self.assertEqual(result['outside_saudi_pixels'], 1)

    def test_encoded_bytes_native_rgba_and_dom_drift_reject_even_exact_png(self):
        for field in ('encoded_sha256', 'native_rgba', 'dom_sha256'):
            with self.subTest(field=field):
                record = copy.deepcopy(self.record)
                if field == 'dom_sha256': record[field] = '3'*64
                elif field == 'native_rgba': record[field][proof.SAUDI]['rgba_sha256'] = '3'*64
                else: record[field][proof.SAUDI] = '3'*64
                with self.assertRaises(AssertionError): self.compare(record=record)

    def test_geometry_filter_scroll_or_dpr_drift_rejects(self):
        for field, value in (('filter','brightness(0.99)'), ('scroll',[0,1001]), ('dpr',2)):
            with self.subTest(field=field):
                record = copy.deepcopy(self.record)
                record['state'][field] = value; record['after_state'][field] = value
                with self.assertRaises(AssertionError): self.compare(record=record)
        record = copy.deepcopy(self.record)
        record['state']['selected'][proof.SAUDI]['rect'][0] += 1
        record['after_state'] = copy.deepcopy(record['state'])
        with self.assertRaises(AssertionError): self.compare(record=record)

    def test_missing_proof_or_unverified_rectangle_cannot_grant_allowance(self):
        for field in ('encoded_sha256', 'native_rgba', 'dom_sha256', 'state'):
            record = copy.deepcopy(self.record); del record[field]
            with self.subTest(field=field), self.assertRaises(AssertionError): self.compare(record=record)
        for field in ('target_unobscured', 'saudi_unobscured'):
            record = copy.deepcopy(self.record)
            record['state'][field] = False; record['after_state'][field] = False
            with self.subTest(field=field), self.assertRaises(AssertionError): self.compare(record=record)
        record = copy.deepcopy(self.record); record['allow_rectangle'] = [0,0,30,20]
        with self.assertRaises(AssertionError): self.compare(record=record)

    def test_capture_motion_header_overlap_and_wrong_size_rejects(self):
        record = copy.deepcopy(self.record); record['after_state']['scroll'] = [0, 1001]
        with self.assertRaises(AssertionError): self.compare(record=record)
        record = copy.deepcopy(self.record); record['state']['header'][3] = 30
        record['after_state'] = copy.deepcopy(record['state'])
        with self.assertRaises(AssertionError): self.compare(record=record)
        with self.assertRaises(AssertionError): self.compare(Image.new('RGBA', (29,20)))

    def test_grid_clip_bounds_cannot_allow_hidden_saudi_pixels(self):
        record = copy.deepcopy(self.record)
        record['target'] = next(identity for identity in proof.ENCODED if identity != proof.SAUDI)
        record['state']['selected'][proof.SAUDI]['grid'] = [4,50,26,20]
        record['after_state'] = copy.deepcopy(record['state'])
        image = self.image.copy(); image.putpixel((2, 2), (101,100,100,255))
        result = proof.compare(self.image, image, record, record)
        self.assertFalse(result['passed']); self.assertEqual(result['outside_saudi_pixels'], 1)


if __name__ == '__main__': unittest.main()
