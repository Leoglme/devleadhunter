"""Resolve the right :class:`PaymentProviderClient` from a stored account.

Token freshness is the caller's concern: for Qonto, pass an already-valid access
token (refreshed and re-persisted by ``payment_account_service``, since Qonto
refresh tokens rotate). Stripe needs no per-user token — it runs on the platform
key with the ``Stripe-Account`` header.
"""

from enums.payment_provider import PaymentProvider
from models.payment_account import PaymentAccount
from services.payment_providers.base import PaymentProviderClient
from services.payment_providers.qonto_provider import QontoPaymentProvider
from services.payment_providers.stripe_provider import StripePaymentProvider


def get_payment_provider(account: PaymentAccount, *, qonto_access_token: str | None = None) -> PaymentProviderClient:
    """
    Build the encashment client for a connected account.

    Args:
        account: The user's connected payment account.
        qonto_access_token: A valid Qonto access token (required for Qonto).

    Returns:
        The provider client matching ``account.provider``.

    Raises:
        ValueError: On an unknown provider, or a Qonto account with no token.
    """
    if account.provider == PaymentProvider.QONTO.value:
        if not qonto_access_token:
            raise ValueError("A valid Qonto access token is required to build the Qonto provider.")
        return QontoPaymentProvider(account, qonto_access_token)
    if account.provider == PaymentProvider.STRIPE.value:
        return StripePaymentProvider(account)
    raise ValueError(f"Unknown payment provider: {account.provider!r}")
