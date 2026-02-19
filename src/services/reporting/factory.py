"""
Factory for creating report generators based on file extension.
"""
import os
from typing import Type

from src.core.interfaces import ReportGenerator
from .exceptions import UnsupportedReportFormatError
from .excel_generator import ExcelReportGenerator
from .json_generator import JsonReportGenerator


class ReportFactory:
    """
    Factory class to instantiate the correct ReportGenerator implementation.
    """

    @staticmethod
    def get_generator(output_path: str) -> ReportGenerator:
        """
        Returns a report generator suitable for the given output path extension.

        Args:
            output_path: The file path where the report will be saved.

        Returns:
            An instance of a class implementing ReportGenerator.

        Raises:
            UnsupportedReportFormatError: If the file extension is not supported.
        """
        _, ext = os.path.splitext(output_path)
        ext = ext.lower()

        if ext == '.xlsx':
            return ExcelReportGenerator()
        elif ext == '.json':
            return JsonReportGenerator()
        else:
            raise UnsupportedReportFormatError(
                f"Unsupported report format '{ext}'. Supported formats: .xlsx, .json"
            )
