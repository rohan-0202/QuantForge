from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ReturnLogs:
    def __init__(self):
        self._logs = {}
        for log_level in LogLevel:
            self._logs[log_level] = []

    def add_log(self, log_level: LogLevel, message: str):
        self._logs[log_level].append(message)

    def get_logs(self):
        return self._logs

    def get_log_messages(self, log_level: LogLevel):
        return self._logs[log_level]
