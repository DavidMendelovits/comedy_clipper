"""
Progress Reporting
Standardized progress reporting for UI consumption
"""

import json
import sys
from typing import Optional


class ProgressReporter:
    """Standardized progress reporter for clippers"""

    def __init__(self, json_output: bool = False):
        """
        Initialize progress reporter

        Args:
            json_output: Output only JSON-formatted progress (no text)
        """
        self.json_output = json_output

    def emit(
        self,
        phase: str,
        percent: int,
        current: Optional[int] = None,
        total: Optional[int] = None,
        message: Optional[str] = None
    ):
        """
        Emit progress update

        Args:
            phase: Processing phase (e.g., "loading", "detection", "clipping")
            percent: Progress percentage (0-100)
            current: Current item number (optional)
            total: Total item count (optional)
            message: Progress message (optional)
        """
        progress_data = {
            "type": "progress",
            "phase": phase,
            "percent": min(100, max(0, percent))  # Clamp to 0-100
        }

        if current is not None:
            progress_data["current"] = current
        if total is not None:
            progress_data["total"] = total
        if message:
            progress_data["message"] = message

        print(f"[PROGRESS] {json.dumps(progress_data)}")
        sys.stdout.flush()

    def step(self, message: str):
        """
        Emit a processing step message

        Args:
            message: Step description
        """
        print(f"[STEP] {message}")
        sys.stdout.flush()

    def log(self, message: str, level: str = "info"):
        """
        Emit a log message

        Args:
            message: Log message
            level: Log level (info, warning, error)
        """
        if not self.json_output:
            prefix = {
                "info": "[INFO]",
                "warning": "[WARNING]",
                "error": "[ERROR]"
            }.get(level, "[LOG]")
            print(f"{prefix} {message}")
        else:
            log_data = {
                "type": "log",
                "level": level,
                "message": message
            }
            print(f"[LOG] {json.dumps(log_data)}")

        sys.stdout.flush()

    def error(self, message: str, exception: Optional[Exception] = None):
        """
        Report an error

        Args:
            message: Error message
            exception: Optional exception object
        """
        error_data = {
            "type": "error",
            "message": message
        }

        if exception:
            error_data["exception"] = str(exception)
            error_data["exception_type"] = type(exception).__name__

        print(f"[ERROR] {json.dumps(error_data)}")
        sys.stdout.flush()

    def complete(self, message: str = "Processing complete"):
        """
        Report completion

        Args:
            message: Completion message
        """
        self.emit("complete", 100, message=message)

        if not self.json_output:
            print(f"\n✓ {message}")
            sys.stdout.flush()


class SilentProgressReporter(ProgressReporter):
    """Progress reporter that outputs nothing (for testing/batch processing)"""

    def emit(self, *args, **kwargs):
        pass

    def step(self, *args, **kwargs):
        pass

    def log(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def complete(self, *args, **kwargs):
        pass
