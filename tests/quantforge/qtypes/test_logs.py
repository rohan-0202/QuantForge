import unittest
from quantforge.qtypes.logs import LogLevel, ReturnLogs


class TestLogLevel(unittest.TestCase):
    def test_log_level_values(self):
        """Test that LogLevel enum has correct values."""
        self.assertEqual(LogLevel.DEBUG.value, "DEBUG")
        self.assertEqual(LogLevel.INFO.value, "INFO")
        self.assertEqual(LogLevel.WARNING.value, "WARNING")
        self.assertEqual(LogLevel.ERROR.value, "ERROR")
        self.assertEqual(LogLevel.CRITICAL.value, "CRITICAL")


class TestReturnLogs(unittest.TestCase):
    def setUp(self):
        """Set up a ReturnLogs instance for each test."""
        self.logs = ReturnLogs()

    def test_init(self):
        """Test that ReturnLogs initializes with empty logs for each level."""
        logs_dict = self.logs.get_logs()
        self.assertEqual(len(logs_dict), len(LogLevel))
        for level in LogLevel:
            self.assertIn(level, logs_dict)
            self.assertEqual(logs_dict[level], [])

    def test_add_log(self):
        """Test adding logs at different levels."""
        self.logs.add_log(LogLevel.INFO, "Test info message")
        self.logs.add_log(LogLevel.ERROR, "Test error message")
        self.logs.add_log(LogLevel.INFO, "Another info message")

        info_logs = self.logs.get_log_messages(LogLevel.INFO)
        error_logs = self.logs.get_log_messages(LogLevel.ERROR)
        debug_logs = self.logs.get_log_messages(LogLevel.DEBUG)

        self.assertEqual(len(info_logs), 2)
        self.assertEqual(len(error_logs), 1)
        self.assertEqual(len(debug_logs), 0)
        self.assertEqual(info_logs, ["Test info message", "Another info message"])
        self.assertEqual(error_logs, ["Test error message"])

    def test_get_logs(self):
        """Test retrieving all logs."""
        self.logs.add_log(LogLevel.DEBUG, "Debug message")
        self.logs.add_log(LogLevel.CRITICAL, "Critical message")

        logs_dict = self.logs.get_logs()
        self.assertEqual(logs_dict[LogLevel.DEBUG], ["Debug message"])
        self.assertEqual(logs_dict[LogLevel.CRITICAL], ["Critical message"])
        self.assertEqual(logs_dict[LogLevel.INFO], [])

    def test_get_log_messages(self):
        """Test retrieving log messages for a specific level."""
        self.logs.add_log(LogLevel.WARNING, "Warning 1")
        self.logs.add_log(LogLevel.WARNING, "Warning 2")

        warning_logs = self.logs.get_log_messages(LogLevel.WARNING)
        self.assertEqual(warning_logs, ["Warning 1", "Warning 2"])


if __name__ == "__main__":
    unittest.main()
