from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from jose import jwt

from adversaria.api import routes


def test_authenticate_credentials_returns_short_lived_token():
    settings = routes._settings.model_copy(
        update={
            "auth_email": "user@example.com",
            "auth_password": "correct horse battery staple",
            "jwt_secret": "test-signing-secret-for-auth-tests-32-chars",
            "jwt_algorithm": "HS256",
        }
    )

    with patch.object(routes, "_settings", settings):
        response = routes.authenticate_credentials("USER@example.com", "correct horse battery staple")

    claims = jwt.decode(
        response["access_token"],
        "test-signing-secret-for-auth-tests-32-chars",
        algorithms=["HS256"],
    )
    assert claims["sub"] == "user@example.com"
    assert claims["exp"] > datetime.now(timezone.utc).timestamp()
    assert response["expires_in"] == 1800


@pytest.mark.parametrize(
    ("email", "password", "status_code"),
    [
        ("user@example.com", "wrong", 401),
        ("wrong@example.com", "correct horse battery staple", 401),
        ("user@example.com", "correct horse battery staple", 503),
    ],
)
def test_authenticate_credentials_rejects_invalid_or_unconfigured(
    email: str, password: str, status_code: int
):
    settings = routes._settings.model_copy(
        update={
            "auth_email": "" if status_code == 503 else "user@example.com",
            "auth_password": "" if status_code == 503 else "correct horse battery staple",
            "jwt_secret": "test-signing-secret-for-auth-tests-32-chars",
        }
    )

    with patch.object(routes, "_settings", settings), pytest.raises(HTTPException) as exc_info:
        routes.authenticate_credentials(email, password)

    assert exc_info.value.status_code == status_code


@pytest.mark.parametrize("secret", ["change-me", "too-short"])
def test_jwt_secret_must_be_private_and_long_enough(secret: str):
    settings = routes._settings.model_copy(update={"jwt_secret": secret})

    with patch.object(routes, "_settings", settings), pytest.raises(HTTPException) as exc_info:
        routes.ensure_jwt_secret_configured()

    assert exc_info.value.status_code == 503