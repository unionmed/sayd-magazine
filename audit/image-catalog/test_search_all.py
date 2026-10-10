#!/usr/bin/env python3
"""Offline tests for the read-only historical image catalog."""
import importlib.util
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("catalog", HERE / "search_all.py")
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)

class CatalogTests(unittest.TestCase):
    def test_manifest_count(self):
        rows = list(catalog.records())
        self.assertEqual(len(rows), 10184)
        self.assertEqual(len({r["path"] for r in rows}), len(rows))
    def test_sha_integrity(self):
        result = catalog.audit(list(catalog.records()))
        self.assertFalse(result["invalid_records"])
        self.assertFalse(result["duplicate_path_entries"])
        self.assertGreaterEqual(result["duplicate_content_extra_paths"], 1)
    def test_search_read_only(self):
        rows = list(catalog.records())
        found = catalog.query(rows, "رماية", limit=5)
        self.assertLessEqual(len(found), 5)
        self.assertTrue(all(x["visual_status"] == "UNVERIFIED" for x in found))
    def test_normalize_arabic(self):
        self.assertEqual(catalog.normalize("إلى"), catalog.normalize("الى"))
    def test_false_positive_person_name(self):
        self.assertNotIn("الطيور", catalog.candidate_sections("docs/media/uploads/2013/03/عبد-العزيز-البابطين.jpg"))
    def test_actual_duck_keyword(self):
        self.assertIn("الطيور", catalog.candidate_sections("docs/media/uploads/2013/03/انيس-وصيد-البط-في-الفرات.jpg"))
    def test_unknown_not_forced(self):
        self.assertEqual(catalog.candidate_sections("docs/media/uploads/2013/03/MED-136164168818-519-9.jpg"), ["غير مصنف"])
    def test_no_writes_in_search(self):
        self.assertEqual(catalog.query([], "صقر"), [])

if __name__ == "__main__":
    unittest.main()
