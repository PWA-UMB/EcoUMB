import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.keys import generate_rsa_keypair
from app.core.rate_limit import SlidingWindowRateLimiter
from app.main import create_app


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


# ---------------------------------------------------------------------- config
def test_production_requires_jwt_keys() -> None:
    with pytest.raises(ValidationError, match="JWT_PRIVATE_KEY"):
        _settings(app_env="production")


def test_production_rejects_wildcard_cors() -> None:
    private, public = generate_rsa_keypair()

    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        _settings(
            app_env="production", jwt_private_key=private, jwt_public_key=public, cors_origins="*"
        )


def test_cors_origins_are_split_and_trimmed() -> None:
    settings = _settings(cors_origins=" http://a.test , http://b.test,")

    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


def test_only_one_jwt_key_is_a_configuration_error() -> None:
    private, _ = generate_rsa_keypair()

    with pytest.raises(ValueError, match="juntas"):
        create_app(_settings(app_env="test", jwt_private_key=private))


def test_escaped_newlines_in_pem_env_values_are_accepted() -> None:
    private, public = generate_rsa_keypair()
    escaped = {
        "jwt_private_key": private.replace("\n", "\\n"),
        "jwt_public_key": public.replace("\n", "\\n"),
    }

    app = create_app(
        _settings(app_env="test", database_url="sqlite+pysqlite:///:memory:", **escaped)
    )

    assert app.state.token_service.private_key == private


# --------------------------------------------------------------------- limiter
def test_rate_limiter_blocks_then_recovers_after_the_window() -> None:
    now = [0.0]
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60, clock=lambda: now[0])

    assert limiter.retry_after("ip") is None
    assert limiter.retry_after("ip") is None
    wait = limiter.retry_after("ip")
    assert wait is not None and 0 < wait <= 60

    now[0] = 61.0
    assert limiter.retry_after("ip") is None


def test_rate_limiter_counts_each_key_separately() -> None:
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, clock=lambda: 0.0)

    assert limiter.retry_after("a") is None
    assert limiter.retry_after("b") is None
    assert limiter.retry_after("a") is not None
