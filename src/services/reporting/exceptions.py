"""
Custom exceptions for the reporting service.
"""


class ReportingError(Exception):
    """Base exception for reporting-related errors."""
    pass


class UnsupportedReportFormatError(ReportingError):
    """Raised when a report format is not supported."""
    pass
