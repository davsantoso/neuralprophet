"""Ensure the frozen research snapshot matches its recorded hashes."""

import json
from pathlib import Path
import unittest

from audit_provenance import build_manifest


class ProvenanceTests(unittest.TestCase):
    def test_frozen_data_report_and_environment(self):
        expected = json.loads(Path("artifacts/provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(build_manifest(), expected)


if __name__ == "__main__":
    unittest.main()
