from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from auth import GoogleClaims, VerificationError, verify_google_id_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AUDIENCE = "test-client-id"
_VALID_ISSUERS: frozenset[str] = frozenset(["accounts.google.com", "https://accounts.google.com"])


@pytest.fixture(scope="module")
def rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _make_token(
    rsa_key: rsa.RSAPrivateKey,
    *,
    iss: str = "accounts.google.com",
    aud: str = _AUDIENCE,
    sub: str = "user-123",
    email: str = "user@example.com",
    exp_offset: int = 3600,
    kid: str = "key-1",
) -> str:
    now = int(time.time())
    payload = {
        "iss": iss,
        "aud": aud,
        "sub": sub,
        "email": email,
        "iat": now,
        "exp": now + exp_offset,
    }
    return jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": kid})


def _build_jwks(rsa_key: rsa.RSAPrivateKey, kid: str = "key-1") -> dict[str, object]:
    """Return a JWKS payload dict containing the public key."""
    pub = rsa_key.public_key()
    jwk_dict = jwt.algorithms.RSAAlgorithm.to_jwk(pub, as_dict=True)
    jwk_dict.update({"kty": "RSA", "use": "sig", "alg": "RS256", "kid": kid})
    return {"keys": [jwk_dict]}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_valid_token_returns_claims(rsa_key: rsa.RSAPrivateKey) -> None:
    token = _make_token(rsa_key)
    jwks = _build_jwks(rsa_key)
    now_utc = int(time.time())

    result = verify_google_id_token(token, jwks, _AUDIENCE, now_utc, _VALID_ISSUERS)

    assert isinstance(result, GoogleClaims)
    assert result.sub == "user-123"
    assert result.email == "user@example.com"


def test_expired_token_raises(rsa_key: rsa.RSAPrivateKey) -> None:
    token = _make_token(rsa_key, exp_offset=-1)
    jwks = _build_jwks(rsa_key)
    now_utc = int(time.time())

    with pytest.raises(VerificationError, match="Token expired"):
        verify_google_id_token(token, jwks, _AUDIENCE, now_utc, _VALID_ISSUERS)


def test_invalid_issuer_raises(rsa_key: rsa.RSAPrivateKey) -> None:
    token = _make_token(rsa_key, iss="evil.example.com")
    jwks = _build_jwks(rsa_key)
    now_utc = int(time.time())

    with pytest.raises(VerificationError, match="Invalid issuer"):
        verify_google_id_token(token, jwks, _AUDIENCE, now_utc, _VALID_ISSUERS)


def test_custom_valid_issuers_accepted(rsa_key: rsa.RSAPrivateKey) -> None:
    custom_issuer = "http://fake-oauth.test"
    token = _make_token(rsa_key, iss=custom_issuer)
    jwks = _build_jwks(rsa_key)
    now_utc = int(time.time())

    result = verify_google_id_token(token, jwks, _AUDIENCE, now_utc, frozenset([custom_issuer]))

    assert result.email == "user@example.com"


def test_custom_valid_issuers_rejects_google_issuer(rsa_key: rsa.RSAPrivateKey) -> None:
    token = _make_token(rsa_key, iss="accounts.google.com")
    jwks = _build_jwks(rsa_key)
    now_utc = int(time.time())

    with pytest.raises(VerificationError, match="Invalid issuer"):
        verify_google_id_token(token, jwks, _AUDIENCE, now_utc, frozenset(["http://fake-oauth.test"]))


def test_wrong_audience_raises(rsa_key: rsa.RSAPrivateKey) -> None:
    token = _make_token(rsa_key, aud="other-client")
    jwks = _build_jwks(rsa_key)
    now_utc = int(time.time())

    with pytest.raises(VerificationError):
        verify_google_id_token(token, jwks, _AUDIENCE, now_utc, _VALID_ISSUERS)


def test_unknown_kid_raises(rsa_key: rsa.RSAPrivateKey) -> None:
    token = _make_token(rsa_key, kid="unknown-kid")
    jwks = _build_jwks(rsa_key, kid="key-1")  # JWKS has "key-1", token has "unknown-kid"
    now_utc = int(time.time())

    with pytest.raises(VerificationError):
        verify_google_id_token(token, jwks, _AUDIENCE, now_utc, _VALID_ISSUERS)
