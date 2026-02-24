"""
Factory for creating report generators.
"""
import logging
from typing import Dict, Type

from src.core.interfaces import ReportGenerator
from src.services.reporting.excel_generator import ExcelReportGenerator
from src.services.reporting.json_generator import JsonReportGenerator
from src.services.reporting.exceptions import UnsupportedReportFormatError

logger = logging.getLogger(__name__)


class ReportFactory:
    """
    Factory for creating report generators.
    """
    _generators: Dict[str, Type[ReportGenerator]] = {
        "excel": ExcelReportGenerator,
        "json": JsonReportGenerator
    }

    @classmethod
    def register(cls, format_key: str, generator_cls: Type[ReportGenerator]) -> None:
        """
        Registers a new report generator.

        Args:
            format_key: The format identifier (e.g., 'pdf').
            generator_cls: The generator class.
        """
        cls._generators[format_key.lower()] = generator_cls
        logger.info("Registered report generator for format: %s", format_key)

    @classmethod
    def get_generator(cls, format_key: str) -> ReportGenerator:
        """
        Retrieves a report generator instance for the specified format.

        Args:
            format_key: The format identifier.

        Returns:
            An instance of the requested ReportGenerator.

        Raises:
            UnsupportedReportFormatError: If the format is not supported.
        """
        key = format_key.lower()
        if key not in cls._generators:
            raise UnsupportedReportFormatError(f"Report format '{format_key}' is not supported.")

        generator_cls = cls._generators[key]
        # In a more complex system, we might use a DI container here
        return generator_cls()
