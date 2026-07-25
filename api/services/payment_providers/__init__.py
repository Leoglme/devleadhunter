"""Encashment providers — one abstraction, two implementations (Qonto, Stripe).

The rest of the app talks to :class:`PaymentProviderClient`; only this package
knows whether a sale is invoiced through Qonto or Stripe. See
``get_payment_provider`` for resolving the right client from a stored
:class:`~models.payment_account.PaymentAccount`.
"""

from services.payment_providers.base import (
    BillingClient,
    InvoiceRequest,
    IssuedInvoice,
    PaymentProviderClient,
    PaymentState,
)
from services.payment_providers.factory import get_payment_provider

__all__ = [
    "BillingClient",
    "InvoiceRequest",
    "IssuedInvoice",
    "PaymentProviderClient",
    "PaymentState",
    "get_payment_provider",
]
