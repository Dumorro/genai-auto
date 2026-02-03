"""PII (Personally Identifiable Information) protection module."""

import re
from typing import Optional
import structlog

from src.api.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class PIIMasker:
    """Mask PII data in text for security and compliance."""

    # Regex patterns for common PII
    PATTERNS = {
        "ssn": {
            "pattern": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
            "mask": "***-**-****",
            "description": "Social Security Number (US)",
        },
        "email": {
            "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "mask": "***@***.***",
            "description": "Email address",
        },
        "phone_us": {
            "pattern": r"\b(?:\+1\s?)?(?:\(?\d{3}\)?\s?)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "mask": "(***) ***-****",
            "description": "US phone number",
        },
        "phone_intl": {
            "pattern": r"\b\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b",
            "mask": "+** *** *** ****",
            "description": "International phone number",
        },
        "credit_card": {
            "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "mask": "**** **** **** ****",
            "description": "Credit card number",
        },
        "vin": {
            "pattern": r"\b[A-HJ-NPR-Z0-9]{17}\b",
            "mask": "*****************",
            "description": "Vehicle Identification Number",
        },
        "license_plate_us": {
            "pattern": r"\b[A-Z0-9]{1,7}\b",
            "mask": "*******",
            "description": "US license plate",
        },
        "drivers_license": {
            "pattern": r"\b[A-Z]\d{7,8}\b",
            "mask": "*********",
            "description": "Driver's license number",
        },
    }

    def __init__(self, enabled: bool = None):
        self.enabled = enabled if enabled is not None else settings.mask_pii

    def mask(self, text: str, patterns: list[str] = None) -> str:
        """Mask PII in text.
        
        Args:
            text: Text to mask
            patterns: Specific patterns to mask (default: all)
            
        Returns:
            Text with PII masked
        """
        if not self.enabled or not text:
            return text

        patterns_to_use = patterns or list(self.PATTERNS.keys())
        masked_text = text

        for pattern_name in patterns_to_use:
            if pattern_name in self.PATTERNS:
                pattern_info = self.PATTERNS[pattern_name]
                masked_text = re.sub(
                    pattern_info["pattern"],
                    pattern_info["mask"],
                    masked_text,
                    flags=re.IGNORECASE,
                )

        return masked_text

    def detect(self, text: str) -> list[dict]:
        """Detect PII in text without masking.
        
        Returns:
            List of detected PII with type and position
        """
        if not text:
            return []

        detected = []

        for pattern_name, pattern_info in self.PATTERNS.items():
            matches = re.finditer(
                pattern_info["pattern"],
                text,
                flags=re.IGNORECASE,
            )
            for match in matches:
                detected.append({
                    "type": pattern_name,
                    "description": pattern_info["description"],
                    "start": match.start(),
                    "end": match.end(),
                    "value_masked": pattern_info["mask"],
                })

        return detected

    def has_pii(self, text: str) -> bool:
        """Check if text contains PII."""
        return len(self.detect(text)) > 0


class PIILogger:
    """Logger wrapper that masks PII automatically."""

    def __init__(self, logger: structlog.BoundLogger, masker: PIIMasker = None):
        self._logger = logger
        self._masker = masker or PIIMasker()

    def _mask_kwargs(self, kwargs: dict) -> dict:
        """Mask PII in log kwargs."""
        masked = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                masked[key] = self._masker.mask(value)
            elif isinstance(value, dict):
                masked[key] = self._mask_kwargs(value)
            else:
                masked[key] = value
        return masked

    def info(self, message: str, **kwargs):
        self._logger.info(self._masker.mask(message), **self._mask_kwargs(kwargs))

    def warning(self, message: str, **kwargs):
        self._logger.warning(self._masker.mask(message), **self._mask_kwargs(kwargs))

    def error(self, message: str, **kwargs):
        self._logger.error(self._masker.mask(message), **self._mask_kwargs(kwargs))

    def debug(self, message: str, **kwargs):
        self._logger.debug(self._masker.mask(message), **self._mask_kwargs(kwargs))


def get_pii_safe_logger() -> PIILogger:
    """Get a PII-safe logger instance."""
    return PIILogger(structlog.get_logger())


# Global instance
pii_masker = PIIMasker()
