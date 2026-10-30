"""Ensure the frozen research snapshot matches its recorded hashes."""

import json
import os
from pathlib import Path
import unittest

from audit_provenance import build_manifest


class ProvenanceTests(unittest.TestCase):
    def test_frozen_data_report_and_environment(self):
        expected = json.loads(Path("artifacts/provenance.json").read_text(encoding="utf-8"))
        actual = build_manifest()
        if os.environ.get("CI"):
            # CI runs on Linux with CPU torch, not the research environment;
            # data and report hashes are still checked byte for byte.
            del expected["environment"], actual["environment"]
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
