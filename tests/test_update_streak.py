"""Refresh failures must preserve the published card and its retrieval time."""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.update_streak import END, START, publish_snapshot


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.candidate = self.root / "candidate.svg"
        self.output = self.root / "published.svg"
        self.readme = self.root / "README.md"
        self.original = f"Before\n{START}\nPrevious retrieval time\n{END}\nAfter\n"
        self.readme.write_text(self.original, encoding="utf-8")
        self.output.write_bytes(b"previous valid snapshot")
        # Zero is valid, and must never be replaced with a made-up fallback.
        self.valid = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 495 195">
          <text>Total Contributions</text><text>0</text>
          <text>Current Streak</text><text>0</text>
          <text>Longest Streak</text><text>0</text>
        </svg>'''

    def publish(self):
        publish_snapshot(self.candidate, self.output, self.readme,
                         datetime(2026, 10, 31, 9, 0, tzinfo=timezone.utc))

    def assert_preserved(self):
        self.assertEqual(self.output.read_bytes(), b"previous valid snapshot")
        self.assertEqual(self.readme.read_text(encoding="utf-8"), self.original)

    def test_valid_zero_stats_preserve_provider_bytes_and_date_the_snapshot(self):
        self.candidate.write_bytes(self.valid)
        self.publish()
        self.assertEqual(self.output.read_bytes(), self.valid)
        content = self.readme.read_text(encoding="utf-8")
        self.assertIn("2026-10-31 12:00 (Asia/Amman)", content)
        self.assertTrue(content.startswith("Before\n"))
        self.assertTrue(content.endswith("After\n"))

    def test_error_response_does_not_replace_snapshot_or_timestamp(self):
        for response in (b"<html>Rate limited</html>", b"", b"<svg"):
            with self.subTest(response=response):
                self.candidate.write_bytes(response)
                with self.assertRaises((ValueError, ET.ParseError)):
                    self.publish()
                self.assert_preserved()

    def test_svg_error_card_does_not_replace_snapshot(self):
        self.candidate.write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 495 195"><text>API unavailable</text></svg>')
        with self.assertRaises(ValueError):
            self.publish()
        self.assert_preserved()

    def test_missing_stat_does_not_replace_snapshot(self):
        self.candidate.write_bytes(self.valid.replace(b"<text>0</text>", b"<text>Unavailable</text>", 1))
        with self.assertRaises(ValueError):
            self.publish()
        self.assert_preserved()

    def test_missing_or_reversed_markers_do_not_replace_snapshot(self):
        self.candidate.write_bytes(self.valid)
        for content in ("No markers", f"{END}\n{START}", f"{START}{START}{END}"):
            with self.subTest(content=content):
                self.original = content
                self.readme.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.publish()
                self.assert_preserved()

    def test_missing_candidate_does_not_replace_snapshot(self):
        with self.assertRaises(FileNotFoundError):
            self.publish()
        self.assert_preserved()


if __name__ == "__main__":
    unittest.main()
