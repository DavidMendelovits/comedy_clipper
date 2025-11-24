"""Unit tests for progress reporting functionality"""

import unittest
import sys
import io
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from python_backend.core.progress import ProgressReporter, SilentProgressReporter


class TestProgressReporter(unittest.TestCase):
    """Test ProgressReporter class"""

    def setUp(self):
        """Set up test fixtures"""
        self.reporter = ProgressReporter()
        # Capture stdout for testing
        self.captured_output = io.StringIO()
        sys.stdout = self.captured_output

    def tearDown(self):
        """Restore stdout"""
        sys.stdout = sys.__stdout__

    def test_emit_basic(self):
        """Test basic progress emission"""
        self.reporter.emit("loading", 50)

        output = self.captured_output.getvalue()
        self.assertIn("[PROGRESS]", output)

        # Parse JSON
        json_str = output.replace("[PROGRESS] ", "").strip()
        data = json.loads(json_str)

        self.assertEqual(data["type"], "progress")
        self.assertEqual(data["phase"], "loading")
        self.assertEqual(data["percent"], 50)

    def test_emit_with_current_total(self):
        """Test progress with current/total values"""
        self.reporter.emit("detection", 75, current=15, total=20)

        output = self.captured_output.getvalue()
        json_str = output.replace("[PROGRESS] ", "").strip()
        data = json.loads(json_str)

        self.assertEqual(data["phase"], "detection")
        self.assertEqual(data["percent"], 75)
        self.assertEqual(data["current"], 15)
        self.assertEqual(data["total"], 20)

    def test_emit_with_message(self):
        """Test progress with custom message"""
        self.reporter.emit("clipping", 30, message="Creating clip 3/10")

        output = self.captured_output.getvalue()
        json_str = output.replace("[PROGRESS] ", "").strip()
        data = json.loads(json_str)

        self.assertEqual(data["message"], "Creating clip 3/10")

    def test_step(self):
        """Test step message reporting"""
        self.reporter.step("Filtering segments")

        output = self.captured_output.getvalue()
        self.assertIn("[STEP]", output)
        self.assertIn("Filtering segments", output)

    def test_log(self):
        """Test log message emission"""
        self.reporter.log("Test log message")

        output = self.captured_output.getvalue()
        # Default log level is "info", which prints [INFO]
        self.assertIn("[INFO]", output)
        self.assertIn("Test log message", output)

    def test_error(self):
        """Test error message emission"""
        self.reporter.error("Test error message")

        output = self.captured_output.getvalue()
        self.assertIn("[ERROR]", output)
        self.assertIn("Test error message", output)

        json_str = output.replace("[ERROR] ", "").strip()
        data = json.loads(json_str)

        self.assertEqual(data["type"], "error")
        self.assertEqual(data["message"], "Test error message")

    def test_complete(self):
        """Test completion message emission"""
        self.reporter.complete("Processing finished successfully")

        output = self.captured_output.getvalue()
        # complete() emits a progress event with phase="complete" + checkmark
        self.assertIn("[PROGRESS]", output)
        self.assertIn("Processing finished successfully", output)
        self.assertIn("✓", output)  # Checkmark

        # Parse the JSON line
        lines = output.strip().split('\n')
        json_line = lines[0]  # First line is the JSON progress
        json_str = json_line.replace("[PROGRESS] ", "")
        data = json.loads(json_str)

        self.assertEqual(data["type"], "progress")
        self.assertEqual(data["phase"], "complete")
        self.assertEqual(data["percent"], 100)
        self.assertEqual(data["message"], "Processing finished successfully")

    def test_multiple_emissions(self):
        """Test multiple progress emissions"""
        self.reporter.emit("detection", 25)
        self.reporter.emit("detection", 50)
        self.reporter.emit("detection", 75)
        self.reporter.emit("detection", 100)

        output = self.captured_output.getvalue()
        lines = output.strip().split('\n')

        # Should have 4 lines
        self.assertEqual(len(lines), 4)

        # Check progression
        for i, line in enumerate(lines):
            json_str = line.replace("[PROGRESS] ", "")
            data = json.loads(json_str)
            expected_percent = 25 * (i + 1)
            self.assertEqual(data["percent"], expected_percent)


class TestSilentProgressReporter(unittest.TestCase):
    """Test SilentProgressReporter class"""

    def setUp(self):
        """Set up test fixtures"""
        self.reporter = SilentProgressReporter()
        # Capture stdout
        self.captured_output = io.StringIO()
        sys.stdout = self.captured_output

    def tearDown(self):
        """Restore stdout"""
        sys.stdout = sys.__stdout__

    def test_silent_emit(self):
        """Test that emit produces no output"""
        self.reporter.emit("loading", 50)
        output = self.captured_output.getvalue()
        self.assertEqual(output, "")

    def test_silent_step(self):
        """Test that step produces no output"""
        self.reporter.step("processing", 5, 10)
        output = self.captured_output.getvalue()
        self.assertEqual(output, "")

    def test_silent_log(self):
        """Test that log produces no output"""
        self.reporter.log("This should not appear")
        output = self.captured_output.getvalue()
        self.assertEqual(output, "")

    def test_silent_error(self):
        """Test that error produces no output"""
        self.reporter.error("This error should not appear")
        output = self.captured_output.getvalue()
        self.assertEqual(output, "")

    def test_silent_complete(self):
        """Test that complete produces no output"""
        self.reporter.complete("Done")
        output = self.captured_output.getvalue()
        self.assertEqual(output, "")


if __name__ == '__main__':
    unittest.main()
