"""
app/core/exceptions.py
Custom exception hierarchy for NutriGuard AI.
"""


class NutriGuardError(Exception):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class ExtractionError(NutriGuardError):
    pass


class ValidationError(NutriGuardError):
    pass


class RegulatoryEngineError(NutriGuardError):
    pass


class NutriScoreError(NutriGuardError):
    pass


class PipelineError(NutriGuardError):
    pass


class ConfigurationError(NutriGuardError):
    pass


class RateLimitError(NutriGuardError):
    pass