"""Exercise the visible Streamlit workflow without starting cloud training."""

import unittest

from streamlit.testing.v1 import AppTest


class AppWorkflowTests(unittest.TestCase):
    def test_data_and_upload_flow(self):
        app = AppTest.from_file("app.py").run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual([tab.label for tab in app.tabs], ["Ringkasan", "Data", "Evaluasi model", "Eksperimen"])
        self.assertEqual(app.metric[0].value, "114")

        app.checkbox[0].set_value(True).run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("115 observasi" in item.value for item in app.caption))

        app.file_uploader[0].set_value(("agustus.csv", b"ds,bongkar,muat\n2026-08,10000,15000\n", "text/csv")).run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("116 observasi" in item.value for item in app.success))

        app.file_uploader[0].set_value(("september.csv", b"ds,bongkar,muat\n2026-09,10000,15000\n", "text/csv")).run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("harus dimulai dari 2026-08" in item.value for item in app.error))


if __name__ == "__main__":
    unittest.main()
