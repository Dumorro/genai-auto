"""PII masking tests."""

import pytest
from src.api.pii import PIIMasker


class TestPIIMasker:
    """PII masking tests."""

    @pytest.fixture
    def masker(self):
        return PIIMasker(enabled=True)

    def test_mask_ssn(self, masker):
        """Test SSN masking."""
        text = "My SSN is 123-45-6789"
        masked = masker.mask(text)

        assert "123-45-6789" not in masked
        assert "***-**-****" in masked

    def test_mask_email(self, masker):
        """Test email masking."""
        text = "Contact me at john.doe@example.com"
        masked = masker.mask(text)

        assert "john.doe@example.com" not in masked
        assert "***@***.***" in masked

    def test_mask_credit_card(self, masker):
        """Test credit card masking."""
        text = "Card number: 4111-1111-1111-1111"
        masked = masker.mask(text)

        assert "4111-1111-1111-1111" not in masked
        assert "**** **** **** ****" in masked

    def test_mask_vin(self, masker):
        """Test VIN masking."""
        text = "Vehicle VIN: 1HGBH41JXMN109186"
        masked = masker.mask(text)

        assert "1HGBH41JXMN109186" not in masked
        assert "*****************" in masked

    def test_mask_phone_us(self, masker):
        """Test US phone number masking."""
        text = "Call me at (555) 123-4567"
        masked = masker.mask(text)

        assert "123-4567" not in masked

    def test_mask_multiple_pii(self, masker):
        """Test masking multiple PII types."""
        text = "Email: test@example.com, SSN: 123-45-6789, Card: 4111-1111-1111-1111"
        masked = masker.mask(text)

        assert "test@example.com" not in masked
        assert "123-45-6789" not in masked
        assert "4111-1111-1111-1111" not in masked

    def test_no_false_positives(self, masker):
        """Test that normal text is not masked."""
        text = "Hello, this is a normal sentence without any PII."
        masked = masker.mask(text)

        assert masked == text

    def test_detect_pii(self, masker):
        """Test PII detection."""
        text = "My email is test@example.com and SSN is 123-45-6789"
        detected = masker.detect(text)

        assert len(detected) >= 2
        types = [d["type"] for d in detected]
        assert "email" in types
        assert "ssn" in types

    def test_has_pii(self, masker):
        """Test has_pii helper."""
        assert masker.has_pii("Email: test@example.com") is True
        assert masker.has_pii("Hello world") is False

    def test_disabled_masker(self):
        """Test that disabled masker returns original text."""
        masker = PIIMasker(enabled=False)
        text = "SSN: 123-45-6789"
        masked = masker.mask(text)

        assert masked == text

    def test_specific_patterns(self, masker):
        """Test masking specific patterns only."""
        text = "Email: test@example.com, SSN: 123-45-6789"
        masked = masker.mask(text, patterns=["email"])

        assert "test@example.com" not in masked
        assert "123-45-6789" in masked  # SSN should not be masked
