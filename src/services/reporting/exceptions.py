"""
Custom exceptions for the reporting service.
"""

class ReportingError(Exception):
    """Base exception for all reporting errors."""
    pass


class UnsupportedReportFormatError(ReportingError):
    """Raised when a requested report format is not supported."""
    pass
