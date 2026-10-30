"""Committed Markdown results must equal what the generators produce from artifacts."""

import json
from pathlib import Path
import unittest

import diagnose
import export_results


class GeneratedDocumentTests(unittest.TestCase):
    def test_result_summary_matches_report(self):
        self.assertEqual(Path("HASIL_EKSPERIMEN.md").read_text(encoding="utf-8"), export_results.build_document())

    def test_diagnostics_document_matches_artifact(self):
        diagnostics = json.loads(Path("artifacts/diagnostics.json").read_text(encoding="utf-8"))
        self.assertEqual(Path("DIAGNOSTIK_PENELITIAN.md").read_text(encoding="utf-8"),
                         "\n".join(diagnose.document_lines(diagnostics)))


if __name__ == "__main__":
    unittest.main()
