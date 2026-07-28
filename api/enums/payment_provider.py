"""Payment providers a user can connect to collect website sales.

Distinct from the platform Stripe account that handles credit purchases
(always Léo's, never per-user): this is the *sales* encashment provider, one
per user. Qonto is admin-only (its OAuth app only covers its own owner's
organization); Stripe Connect is the path for every other user.
"""

from enum import Enum


class PaymentProvider(str, Enum):
    """Encashment provider a user sells through."""

    QONTO = "qonto"
    STRIPE = "stripe"


class PaymentEnvironment(str, Enum):
    """Which provider environment the stored credentials belong to.

    Tagged on the account at connection time so a token minted against the
    sandbox can never be used to hit a real organization, and vice versa.
    """

    SANDBOX = "sandbox"
    PRODUCTION = "production"


PAYMENT_PROVIDER_LABELS: dict[str, str] = {
    PaymentProvider.QONTO.value: "Qonto",
    PaymentProvider.STRIPE.value: "Stripe",
}
