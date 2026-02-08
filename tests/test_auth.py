"""Authentication tests."""

from src.api.auth.jwt_auth import (
    hash_password,
    verify_password,
    create_token,
    decode_token,
    create_tokens,
)


class TestPasswordHashing:
    """Password hashing tests."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "securepassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 20

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "securepassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Test verifying wrong password."""
        password = "securepassword123"
        hashed = hash_password(password)

        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "securepassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTTokens:
    """JWT token tests."""

    def test_create_access_token(self):
        """Test creating access token."""
        token = create_token(
            user_id="user-123",
            email="test@example.com",
            name="Test User",
            token_type="access"
        )

        assert token is not None
        assert len(token) > 50

    def test_create_refresh_token(self):
        """Test creating refresh token."""
        token = create_token(
            user_id="user-123",
            email="test@example.com",
            name="Test User",
            token_type="refresh"
        )

        assert token is not None

    def test_decode_valid_token(self):
        """Test decoding valid token."""
        token = create_token(
            user_id="user-123",
            email="test@example.com",
            name="Test User",
            token_type="access"
        )

        payload = decode_token(token)

        assert payload.sub == "user-123"
        assert payload.email == "test@example.com"
        assert payload.name == "Test User"
        assert payload.type == "access"

    def test_create_tokens_returns_both(self):
        """Test create_tokens returns access and refresh tokens."""
        tokens = create_tokens(
            user_id="user-123",
            email="test@example.com",
            name="Test User"
        )

        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"
        assert tokens.expires_in > 0

    def test_access_and_refresh_tokens_different(self):
        """Test that access and refresh tokens are different."""
        tokens = create_tokens(
            user_id="user-123",
            email="test@example.com",
            name="Test User"
        )

        assert tokens.access_token != tokens.refresh_token
