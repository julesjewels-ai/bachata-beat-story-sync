"""
Service manager for system diagnostics.
"""
import logging
from typing import List

from src.core.interfaces import DiagnosticCheck
from src.core.models import DiagnosticResult, DiagnosticStatus

logger = logging.getLogger(__name__)


class SystemDiagnosticManager:
    """
    Manages and runs system diagnostic checks.
    """

    def __init__(self) -> None:
        self._checks: List[DiagnosticCheck] = []

    def register_check(self, check: DiagnosticCheck) -> None:
        """
        Register a new diagnostic check to be run.

        Args:
            check: An instance implementing the DiagnosticCheck protocol.
        """
        self._checks.append(check)

    def run_diagnostics(self) -> List[DiagnosticResult]:
        """
        Run all registered checks and return their results.

        Returns:
            A list of DiagnosticResult objects.
        """
        results: List[DiagnosticResult] = []
        logger.info("Running system diagnostics (%d checks)...", len(self._checks))

        for check in self._checks:
            try:
                result = check.run()
                results.append(result)

                # Log the result
                if result.status == DiagnosticStatus.FAIL:
                    logger.error("Diagnostic FAIL: %s - %s", result.check_name, result.message)
                elif result.status == DiagnosticStatus.WARN:
                    logger.warning("Diagnostic WARN: %s - %s", result.check_name, result.message)
                else:
                    logger.info("Diagnostic PASS: %s - %s", result.check_name, result.message)

            except Exception as e:
                logger.error("Diagnostic check failed unexpectedly: %s", e)
                results.append(
                    DiagnosticResult(
                        check_name="Unknown Check",
                        status=DiagnosticStatus.FAIL,
                        message="Check failed with unhandled exception",
                        details=str(e)
                    )
                )

        return results
