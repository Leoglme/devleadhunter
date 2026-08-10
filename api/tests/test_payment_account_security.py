"""Security-focused unit tests for the payment-account layer.

Covers the guards added around the money paths: the HMAC-signed Qonto OAuth
state (the callback is unauthenticated), the IBAN checksum (printed on every
invoice), the API-key authorization header (admin fallback) and the Stripe
environment guard (test account never invoiced with a live key).
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

import services.payment_account_service as payment_account_module
from core.config import settings
from services.payment_account_service import (
    PaymentAccountService,
    _is_valid_iban,
    _normalize_iban,
)
from services.payment_providers.qonto_provider import QontoPaymentProvider
from services.payment_providers.stripe_provider import StripeConnectError, StripePaymentProvider


@pytest.fixture(autouse=True)
def _stable_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the signing secret so state signatures are deterministic."""
    monkeypatch.setattr(settings, "secret_key", "test-secret-key")


def test_qonto_state_round_trip() -> None:
    """A freshly minted state resolves back to its user id."""
    service = PaymentAccountService()
    url = service.qonto_authorize_url(42)
    state = url.split("state=")[1].split("&")[0]
    assert service.parse_qonto_state(state) == 42


def test_qonto_state_rejects_tampered_user_id() -> None:
    """Swapping the user id in a valid state breaks the signature."""
    service = PaymentAccountService()
    url = service.qonto_authorize_url(42)
    state = url.split("state=")[1].split("&")[0]
    tampered = state.replace("user_42_", "user_1_")
    assert service.parse_qonto_state(tampered) is None


def test_qonto_state_rejects_unsigned_legacy_shape() -> None:
    """The pre-signature ``user_<id>_<random>`` shape is refused."""
    assert PaymentAccountService().parse_qonto_state("user_1_whatever") is None


def test_qonto_state_rejects_expired() -> None:
    """A state older than the freshness window is refused."""
    service = PaymentAccountService()
    issued_at = int((datetime.now(UTC) - timedelta(hours=2)).timestamp())
    signature = service._sign_qonto_state(42, issued_at)
    assert service.parse_qonto_state(f"user_42_{issued_at}_{signature}") is None


def test_iban_normalization_and_valid_checksum() -> None:
    """A well-formed IBAN passes, whatever the spacing and case."""
    assert _is_valid_iban(_normalize_iban("fr14 2004 1010 0505 0001 3M02 606"))


def test_iban_rejects_bad_checksum_and_shape() -> None:
    """A single-digit typo or a truncated IBAN is refused."""
    assert not _is_valid_iban("FR1420041010050500013M02607")
    assert not _is_valid_iban("FR76")


def test_qonto_api_key_authorization_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """The API-key fallback signs requests with Qonto's ``login:secret`` form."""
    monkeypatch.setattr(settings, "qonto_environment", "sandbox")
    monkeypatch.setattr(settings, "qonto_staging_token", "stg_test")
    account = SimpleNamespace(environment="sandbox", qonto_iban=None)
    provider = QontoPaymentProvider(account, api_credentials=("acme-1234", "sk-secret"))
    assert provider._authorized_headers()["Authorization"] == "acme-1234:sk-secret"


def test_qonto_provider_refuses_no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neither an OAuth token nor an API key → the provider refuses to build."""
    monkeypatch.setattr(settings, "qonto_environment", "sandbox")
    monkeypatch.setattr(settings, "qonto_staging_token", "stg_test")
    account = SimpleNamespace(environment="sandbox", qonto_iban=None)
    with pytest.raises(ValueError):
        QontoPaymentProvider(account)


def test_qonto_api_credentials_decrypts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stored API credentials come back decrypted as a (login, secret) pair."""
    monkeypatch.setattr(payment_account_module.encryption_service, "decrypt", lambda value: value.removeprefix("enc:"))
    account = SimpleNamespace(qonto_api_login="enc:acme-1234", qonto_api_secret="enc:sk-secret")
    assert PaymentAccountService().qonto_api_credentials(account) == ("acme-1234", "sk-secret")


def test_qonto_api_credentials_none_when_absent() -> None:
    """No stored key → None, so the caller falls through to a clean error."""
    account = SimpleNamespace(qonto_api_login=None, qonto_api_secret=None)
    assert PaymentAccountService().qonto_api_credentials(account) is None


def test_stripe_provider_refuses_environment_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """An account onboarded in test mode is never invoiced with a live key."""
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_live_x")
    account = SimpleNamespace(stripe_account_id="acct_1", stripe_charges_enabled=True, environment="sandbox")
    with pytest.raises(StripeConnectError):
        StripePaymentProvider(account)


class _StripeObj(dict):
    """Dict with attribute access, mimicking a Stripe SDK Account object."""

    def __getattr__(self, name: str) -> object:
        return self[name]


def test_refresh_stripe_status_requests_sepa_bank_transfer(monkeypatch: pytest.MonkeyPatch) -> None:
    """After onboarding, refreshing status requests the SEPA bank-transfer capability."""
    import stripe

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    connected = _StripeObj(id="acct_1", charges_enabled=True, details_submitted=True, capabilities={})
    monkeypatch.setattr(stripe.Account, "retrieve", lambda _id, **_: connected)
    modify_calls: dict = {}
    monkeypatch.setattr(stripe.Account, "modify", lambda _id, **kwargs: modify_calls.update({"id": _id, **kwargs}))

    account = SimpleNamespace(stripe_account_id="acct_1")
    db = SimpleNamespace(commit=lambda: None, refresh=lambda _obj: None)
    PaymentAccountService().refresh_stripe_status(db, account)

    assert modify_calls["id"] == "acct_1"
    assert modify_calls["capabilities"] == {"sepa_bank_transfer_payments": {"requested": True}}


def test_refresh_stripe_status_skips_request_when_capability_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """An already-active SEPA capability is not re-requested."""
    import stripe

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    connected = _StripeObj(
        id="acct_1",
        charges_enabled=True,
        details_submitted=True,
        capabilities={"sepa_bank_transfer_payments": "active"},
    )
    monkeypatch.setattr(stripe.Account, "retrieve", lambda _id, **_: connected)

    def _must_not_modify(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("must not re-request an active capability")

    monkeypatch.setattr(stripe.Account, "modify", _must_not_modify)

    account = SimpleNamespace(stripe_account_id="acct_1")
    db = SimpleNamespace(commit=lambda: None, refresh=lambda _obj: None)
    PaymentAccountService().refresh_stripe_status(db, account)
